#!/usr/bin/env python
# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import logging
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Literal, Optional

import torch
import transformers
from peft import PeftConfig, PeftModel
from simpo_config import SimPOConfig
from simpo_trainer import SimPOTrainer
from transformers import AutoModelForCausalLM, set_seed

from alignment import (
    DataArguments,
    DPOConfig,
    H4ArgumentParser,
    ModelArguments,
    get_checkpoint,
    get_datasets,
    get_kbit_device_map,
    get_peft_config,
    get_quantization_config,
    get_tokenizer,
    is_adapter_model,
)
from alignment.data import is_openai_format, maybe_insert_system_message

logger = logging.getLogger(__name__)

MISTRAL_CHAT_TEMPLATE = "{% if messages[0]['role'] == 'system' %}{% set loop_messages = messages[1:] %}{% set system_message = messages[0]['content'].strip() + '\n\n' %}{% else %}{% set loop_messages = messages %}{% set system_message = '' %}{% endif %}{% for message in loop_messages %}{% if loop.index0 == 0 %}{% set content = system_message + message['content'] %}{% else %}{% set content = message['content'] %}{% endif %}{% if message['role'] == 'user' %}{{ '[INST] ' + content.strip() + ' [/INST]' }}{% elif message['role'] == 'assistant' %}{{ ' '  + content.strip() + ' ' + eos_token }}{% endif %}{% endfor %}"


def apply_chat_template(
    example,
    tokenizer,
    task: Literal["sft", "generation", "rm", "simpo"],
    auto_insert_empty_system_msg: bool = True,
    change_template=None,
):
    if change_template == "mistral":
        tokenizer.chat_template = MISTRAL_CHAT_TEMPLATE
    if task in ["sft", "generation"]:
        messages = example["messages"]
        # We add an empty system message if there is none
        if auto_insert_empty_system_msg:
            maybe_insert_system_message(messages, tokenizer)
        example["text"] = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True if task == "generation" else False,
        )
    elif task == "rm":
        if all(k in example.keys() for k in ("chosen", "rejected")):
            chosen_messages = example["chosen"]
            rejected_messages = example["rejected"]
            # We add an empty system message if there is none
            if auto_insert_empty_system_msg:
                maybe_insert_system_message(chosen_messages, tokenizer)
                maybe_insert_system_message(rejected_messages, tokenizer)

            example["text_chosen"] = tokenizer.apply_chat_template(
                chosen_messages, tokenize=False
            )
            example["text_rejected"] = tokenizer.apply_chat_template(
                rejected_messages, tokenize=False
            )
        else:
            raise ValueError(
                f"Could not format example as dialogue for rm task! Require [chosen, rejected] keys but found {list(example.keys())}"
            )
    elif task == "simpo":
        if all(k in example.keys() for k in ("chosen", "rejected")):
            if not is_openai_format(example["chosen"]) or not is_openai_format(
                example["rejected"]
            ):
                raise ValueError(
                    f"Could not format example as dialogue for {task} task! Require OpenAI format for all messages"
                )

            # For DPO/ORPO, the inputs are triples of (prompt, chosen, rejected), where chosen and rejected are the final turn of a dialogue
            # We therefore need to extract the N-1 turns to form the prompt
            if "prompt" in example and is_openai_format(example["prompt"]):
                prompt_messages = example["prompt"]
                chosen_messages = example["chosen"]
                rejected_messages = example["rejected"]
            else:
                prompt_messages = example["chosen"][:-1]
                # Now we extract the final turn to define chosen/rejected responses
                chosen_messages = example["chosen"][-1:]
                rejected_messages = example["rejected"][-1:]

            # Prepend a system message if the first message is not a system message
            if auto_insert_empty_system_msg:
                maybe_insert_system_message(prompt_messages, tokenizer)

            example["text_prompt"] = tokenizer.apply_chat_template(
                prompt_messages, tokenize=False
            )
            example["text_chosen"] = tokenizer.apply_chat_template(
                chosen_messages, tokenize=False
            )
            if example["text_chosen"].startswith(tokenizer.bos_token):
                example["text_chosen"] = example["text_chosen"][
                    len(tokenizer.bos_token) :
                ]
            example["text_rejected"] = tokenizer.apply_chat_template(
                rejected_messages, tokenize=False
            )
            if example["text_rejected"].startswith(tokenizer.bos_token):
                example["text_rejected"] = example["text_rejected"][
                    len(tokenizer.bos_token) :
                ]
        else:
            raise ValueError(
                f"Could not format example as dialogue for {task} task! Require either the "
                f"[chosen, rejected] or [prompt, chosen, rejected] keys but found {list(example.keys())}"
            )
    else:
        raise ValueError(
            f"Task {task} not supported, please ensure that the provided task is one of ['sft', 'generation', 'rm', 'dpo', 'orpo']"
        )
    return example


def main():
    # DeepSpeed設定ファイルパスのみを受け取るカスタムパーサーを作成
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--deepspeed_config", type=str, help="Path to DeepSpeed configuration file"
    )
    parser.add_argument(
        "--local_rank", type=int, default=-1, help="Local rank for distributed training"
    )
    custom_args, _ = parser.parse_known_args()

    # PYTORCH_CUDAのメモリ設定を改善
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # 最大シーケンス長を短くして、メモリ使用量を削減
    MAX_LENGTH = 192  # 元の設定は256
    MAX_PROMPT_LENGTH = 96  # 元の設定は128

    # YAMLの設定をハードコード
    # ModelArgumentsの設定
    model_args = ModelArguments(
        model_name_or_path="princeton-nlp/Llama-3-Base-8B-SFT",
        torch_dtype=None,
        attn_implementation="eager",
    )

    # DataArgumentsの設定
    data_args = DataArguments(
        dataset_mixer={"HuggingFaceH4/ultrafeedback_binarized": 1.0},
        dataset_splits=["train_prefs", "test_prefs"],
        preprocessing_num_workers=12,
        auto_insert_empty_system_msg=True,
    )

    # SimPOConfigの設定
    training_args = SimPOConfig(
        fp16=True,
        beta=2.0,
        gamma_beta_ratio=0.5,
        do_eval=True,
        evaluation_strategy="steps",
        eval_steps=400,
        gradient_accumulation_steps=16,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        hub_model_id="simpo-exps",
        learning_rate=6.0e-7,
        log_level="info",
        logging_steps=5,
        lr_scheduler_type="cosine",
        max_length=MAX_LENGTH,  # 修正: シーケンス長を短く
        max_prompt_length=MAX_PROMPT_LENGTH,  # 修正: プロンプト長を短く
        num_train_epochs=1,
        optim="adamw_torch",
        output_dir="outputs/llama-3-8b-base-simpo",
        run_name="llama-3-8b-base-simpo",
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,  # 修正: 評価バッチサイズを小さく
        push_to_hub=False,
        save_strategy="steps",
        save_steps=1000000,
        report_to=["wandb"],
        save_total_limit=20,
        seed=42,
        warmup_ratio=0.1,
        remove_unused_columns=False,  # DPODataCollatorWithPaddingの警告を修正
    )

    # --deepspeed_configが指定されていればその値を使用し、指定がなければYAMLの値を使用
    if custom_args.deepspeed_config:
        training_args.deepspeed = custom_args.deepspeed_config
    else:
        training_args.deepspeed = "ds_config.json"

    # local_rankの設定
    if custom_args.local_rank >= 0:
        training_args.local_rank = custom_args.local_rank

    #######
    # Setup
    #######
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    log_level = training_args.get_process_log_level()
    logger.setLevel(log_level)
    transformers.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.enable_default_handler()
    transformers.utils.logging.enable_explicit_format()

    # Log on each process the small summary:
    logger.info(f"Model parameters {model_args}")
    logger.info(f"Data parameters {data_args}")
    logger.info(f"Training/evaluation parameters {training_args}")

    # Check for last checkpoint
    last_checkpoint = get_checkpoint(training_args)
    if last_checkpoint is not None and training_args.resume_from_checkpoint is None:
        logger.info(f"Checkpoint detected, resuming training at {last_checkpoint=}.")

    # Set seed for reproducibility
    set_seed(training_args.seed)

    ###############
    # Load datasets
    ###############
    raw_datasets = get_datasets(
        data_args,
        splits=data_args.dataset_splits,
        configs=data_args.dataset_configs,
        columns_to_keep=[
            "messages",
            "chosen",
            "rejected",
            "prompt",
            "completion",
            "label",
        ],
        # seed=training_args.seed,
    )
    logger.info(
        f"Training on the following splits: {[split + ' : ' + str(dset.num_rows) for split, dset in raw_datasets.items()]}"
    )
    column_names = list(raw_datasets["train"].features)

    #####################################
    # Load tokenizer and process datasets
    #####################################
    data_args.truncation_side = (
        "left"  # Truncate from left to ensure we don't lose labels in final turn
    )
    tokenizer = get_tokenizer(model_args, data_args)

    if "mistral" in model_args.model_name_or_path.lower():
        change_template = "mistral"
    else:
        change_template = None
    #####################
    # Apply chat template
    #####################
    raw_datasets = raw_datasets.map(
        apply_chat_template,
        fn_kwargs={
            "tokenizer": tokenizer,
            "task": "simpo",
            "auto_insert_empty_system_msg": data_args.auto_insert_empty_system_msg,
            "change_template": change_template,
        },
        num_proc=data_args.preprocessing_num_workers,
        remove_columns=column_names,
        desc="Formatting comparisons with prompt template",
    )

    # Replace column names with what TRL needs, text_chosen -> chosen and text_rejected -> rejected
    for split in ["train", "test"]:
        raw_datasets[split] = raw_datasets[split].rename_columns(
            {
                "text_prompt": "prompt",
                "text_chosen": "chosen",
                "text_rejected": "rejected",
            }
        )

    # サンプルログを制限して無駄なメモリ使用を避ける
    sample_indices = random.sample(range(min(len(raw_datasets["train"]), 100)), 1)
    for index in sample_indices:
        logger.info(
            f"Prompt sample {index} of the raw training set:\n\n{raw_datasets['train'][index]['prompt'][:200]}..."
        )
        logger.info(
            f"Chosen sample {index} of the raw training set:\n\n{raw_datasets['train'][index]['chosen'][:200]}..."
        )
        logger.info(
            f"Rejected sample {index} of the raw training set:\n\n{raw_datasets['train'][index]['rejected'][:200]}..."
        )

    torch_dtype = (
        model_args.torch_dtype
        if model_args.torch_dtype in ["auto", None]
        else getattr(torch, model_args.torch_dtype)
    )
    quantization_config = get_quantization_config(model_args)

    model_kwargs = dict(
        revision=model_args.model_revision,
        trust_remote_code=model_args.trust_remote_code,
        torch_dtype=torch_dtype,
        use_cache=False,  # 常にキャッシュを無効化
        device_map=(
            "auto" if custom_args.local_rank < 0 else {"": custom_args.local_rank}
        ),
        quantization_config=quantization_config,
        attn_implementation=model_args.attn_implementation,
    )

    model = model_args.model_name_or_path
    training_args.model_init_kwargs = model_kwargs

    # メモリ使用量を減らすためのデータセット制限（必要に応じて）
    # トレーニングデータセットを制限
    max_train_samples = 10000  # 例えば10000サンプルに制限
    if len(raw_datasets["train"]) > max_train_samples:
        raw_datasets["train"] = raw_datasets["train"].select(range(max_train_samples))
        logger.info(f"Training dataset limited to {max_train_samples} samples")

    # テストデータセットを制限
    max_eval_samples = 1000  # 例えば1000サンプルに制限
    if len(raw_datasets["test"]) > max_eval_samples:
        raw_datasets["test"] = raw_datasets["test"].select(range(max_eval_samples))
        logger.info(f"Evaluation dataset limited to {max_eval_samples} samples")

    #########################
    # Instantiate SimPO trainer
    #########################
    trainer = SimPOTrainer(
        model=model,
        args=training_args,
        train_dataset=raw_datasets["train"],
        eval_dataset=raw_datasets["test"],
        tokenizer=tokenizer,
        peft_config=get_peft_config(model_args),
    )

    # キャッシュをクリア
    torch.cuda.empty_cache()

    ###############
    # Training loop
    ###############
    checkpoint = None
    if training_args.resume_from_checkpoint is not None:
        checkpoint = training_args.resume_from_checkpoint
    elif last_checkpoint is not None:
        checkpoint = last_checkpoint

    try:
        train_result = trainer.train(resume_from_checkpoint=checkpoint)
        metrics = train_result.metrics
        metrics["train_samples"] = len(raw_datasets["train"])
        trainer.log_metrics("train", metrics)
        trainer.save_metrics("train", metrics)
        trainer.save_state()

        logger.info("*** Training complete ***")

        ##################################
        # Save model and create model card
        ##################################
        logger.info("*** Save model ***")
        trainer.save_model(training_args.output_dir)
        logger.info(f"Model saved to {training_args.output_dir}")

        # Save everything else on main process
        kwargs = {
            "finetuned_from": model_args.model_name_or_path,
            "dataset": list(data_args.dataset_mixer.keys()),
            "dataset_tags": list(data_args.dataset_mixer.keys()),
            "tags": ["alignment-handbook"],
        }
        if trainer.accelerator.is_main_process:
            trainer.create_model_card(**kwargs)
            # Restore k,v cache for fast inference
            trainer.model.config.use_cache = True
            trainer.model.config.save_pretrained(training_args.output_dir)

        ##########
        # Evaluate
        ##########
        if training_args.do_eval:
            logger.info("*** Evaluate ***")
            metrics = trainer.evaluate()
            metrics["eval_samples"] = len(raw_datasets["test"])
            trainer.log_metrics("eval", metrics)
            trainer.save_metrics("eval", metrics)

        if training_args.push_to_hub is True:
            logger.info("Pushing to hub...")
            trainer.push_to_hub(**kwargs)

        logger.info("*** Training complete! ***")
    except Exception as e:
        logger.error(f"Training failed with error: {e}")
        # エラーが発生した場合でも可能な限りモデルを保存
        try:
            if trainer.accelerator.is_main_process:
                logger.info("Attempting to save partial model...")
                trainer.save_model(training_args.output_dir + "_partial")
        except:
            logger.error("Failed to save partial model")
        raise e


if __name__ == "__main__":
    main()
