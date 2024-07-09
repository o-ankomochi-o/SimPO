# Simple Preference Optimization (SimPO)

This repository contains the code and released models for our paper [SimPO: Simple Preference Optimization with a Reference-Free Reward](https://arxiv.org/abs/2405.14734). We propose a simpler and more effective preference optimization algorithm than DPO (Direct Preference Optimization) without using a reference model. SimPO outperforms DPO and its latest variants across AlpacaEval 2, MT-Bench, and Arena-Hard benchmarks under various settings.

<img src="./SimPO.png" width="1000px"></img>

## 🔗 Quick Links
- [SimPO: Simple Preference Optimization with a Reference-Free Reward](#simple-preference-optimization-simpo)
  - [Tips for Running SimPO](#tips-for-running-simpo)
  - [Released Models](#released-models)
  - [Install Requirements](#install-requirements)
  - [Training scripts](#training-scripts)
  - [Evaluation](#evaluation)
  - [Bugs or Questions?](#bugs-or-questions)
  - [Citation](#citation)

## Tips for Running SimPO
Given the various inquiries about SimPO, we provide a list of tips to help you reproduce our paper results and achieve better outcomes for running SimPO on your own tasks. 
### Hyperparameter tuning
Hyperparameter tuning is crucial for SimPO (and other preference optimization algorithms in general). The three main hyperparameters of SimPO to focus on are `learning_rate`, `beta`, and `gamma`.
- `learning_rate`: It is the most critical hyperparameter for preference optimization. A large learning rate (e.g., 1e-5) can significantly degrade performance, causing the model to produce incoherent sentences or completely repetitive responses. We recommend grid searching over 3e-7, 5e-7, and 1e-6, if resources allow.
- `beta`: Beta controls the reward scaling between winning and losing responses. SimPO requires a much larger `beta` than DPO. In our preprint, we used a beta of `2.0` or `2.5`, but in many cases, an even larger beta (e.g., `10`) could yield better results.
- `gamma`: Gamma controls the target reward margin. We suggest tuning the ratio of gamma to beta (i.e., `gamma / beta`). We recommend using `0.5` as a starting point for `gamma_beta_ratio` and grid searching between `0` and `1`. A well-tuned `gamma_beta_ratio` can provide a modest improvement, but it is not as critical as other hyperparameters.

We used the following hyperparameters for training the released models (note that in our latest update, we changed the hyperparameter `gamma` to `gamma_beta_ratio` as the latter is normalized and easier to tune under different `beta` values).
| Setting           | β   | γ/β   | Learning rate |
|-------------------|-----|-----|----------------|
| Mistral-Base      | 2.0 | 0.8 | 3e-7           |
| Mistral-Instruct  | 2.5 | 0.1 | 5e-7           |
| Llama3-Base       | 2.0 | 0.5 | 6e-7           |
| Llama3-Instruct   | 2.5 | 0.55 | 1e-6           |
| Llama3-Instruct v0.2   | 10 | 0.3 | 1e-6           |

For DPO, we use the following hyperparameters for training.
| Setting                  | β | Learning Rate |
|------------------------|------|---------------|
| Mistral-Base           | 0.01 | 5e-7      |
| Mistral-Instruct       | 0.01 | 2e-7      |
| Llama3-Base            | 0.01 | 5e-7      |
| Llama3-Instruct        | 0.01 | 7e-7      |
| Llama3-Instruct v0.2   | 0.01 | 3e-7      |


### Training and evaluation consistency in BOS
Our released Llama3 models use the initial version of the Llama3 tokenizer (prior to this [PR](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/commit/339ce92d052f002cdbac4a4bd551d1c61dd8345e)). We have found that the updated Llama3 tokenizer with vLLM occasionally introduces two BOS tokens, which can affect evaluation results. Therefore, please ensure that only one BOS token is included in the prompt after applying the Llama3 chat template during any evaluation.

*Notably, if you are training Llama3 and evaluating the trained models on AlpacaEval 2 and Arena-Hard using the templates provided in this repo, please make sure to use the pre-update Llama3 tokenizer (i.e., the one before the PR).*


### Adding an extra sft loss
We have observed that, in some cases, adding an additional SFT loss can help improve results. These findings have been initially validated in the [CPO_SIMPO](https://github.com/fe1ixxu/CPO_SIMPO/tree/main)  repository. We are currently working on integrating this improvement into our main repository.


## Released Models
### v0.1
Below is the complete list of models evaluated in our preprint. We used the [HuggingFaceH4/ultrafeedback_binarized](https://huggingface.co/datasets/HuggingFaceH4/ultrafeedback_binarized) dataset to train the Mistral Base and Llama3 Base models, the [princeton-nlp/mistral-instruct-ultrafeedback](https://huggingface.co/princeton-nlp/mistral-instruct-ultrafeedback) dataset to train the Mistral Instruct models, and the [princeton-nlp/llama3-ultrafeedback](https://huggingface.co/princeton-nlp/llama3-ultrafeedback) dataset to train the Llama3 Instruct models. The latter two datasets are annotated by the [llm-blender/PairRM](https://huggingface.co/llm-blender/PairRM) model.

models                       |                                                                                                           | AE2 LC | AE2 WR |  AH  |
|------------------------------|-----------------------------------------------------------------------------------------------------------|:------:|:------:|:----:|
| Mistral Base 7B SFT          | [alignment-handbook/zephyr-7b-sft-full](https://huggingface.co/alignment-handbook/zephyr-7b-sft-full)     |   8.4  |   6.2  |  1.3 |
| Mistral Base 7B RRHF         | [princeton-nlp/Mistral-7B-Base-SFT-RRHF](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-RRHF) |  11.6  |  10.2  |  6.9 |
| Mistral Base 7B SLiC-HF      | [princeton-nlp/Mistral-7B-Base-SFT-SLiC-HF](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-SLiC-HF) |  10.9  |   8.9  |  7.3 |
| Mistral Base 7B DPO (Zephyr) | [princeton-nlp/Mistral-7B-Base-SFT-DPO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-DPO)     |  15.1  |  12.5  | 10.4 |
| Mistral Base 7B IPO          | [princeton-nlp/Mistral-7B-Base-SFT-IPO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-IPO)     |  11.8  |   9.4  |  7.5 |
| Mistral Base 7B CPO          | [princeton-nlp/Mistral-7B-Base-SFT-CPO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-CPO)     |  13.1  |   9.1  |  5.6 |
| Mistral Base 7B KTO          | [princeton-nlp/Mistral-7B-Base-SFT-KTO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-KTO)     |  13.1  |   9.1  |  5.6 |
| Mistral Base 7B ORPO         | [kaist-ai/mistral-orpo-beta](https://huggingface.co/kaist-ai/mistral-orpo-beta)                           |  14.7  |  12.2  |  7.0 |
| Mistral Base 7B R-DPO        | [princeton-nlp/Mistral-7B-Base-SFT-RDPO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-RDPO)   |  17.4  |  12.8  |  9.9 |
| Mistral Base 7B SimPO        | [princeton-nlp/Mistral-7B-Base-SFT-SimPO](https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-SimPO) |  21.4  |  20.8  | 16.6 |
| Mistral Instruct 7B SFT      | [mistralai/Mistral-7B-Instruct-v0.2](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2)           |  17.1  |  14.7  | 12.6 |
| Mistral Instruct 7B RRHF     | [princeton-nlp/Mistral-7B-Instruct-RRHF](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-RRHF) |  25.3  |  24.8  | 18.1 |
| Mistral Instruct 7B SLiC-HF  | [princeton-nlp/Mistral-7B-Instruct-SLiC-HF](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-SLiC-HF) |  24.1  |  24.6  | 18.9 |
| Mistral Instruct 7B DPO      | [princeton-nlp/Mistral-7B-Instruct-DPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-DPO)     |  26.8  |  24.9  | 16.3 |
| Mistral Instruct 7B IPO      | [princeton-nlp/Mistral-7B-Instruct-IPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-IPO)     |  20.3  |  20.3  | 16.2 |
| Mistral Instruct 7B CPO      | [princeton-nlp/Mistral-7B-Instruct-CPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-CPO)     |  24.5  |  23.6  | 17.9 |
| Mistral Instruct 7B KTO      | [princeton-nlp/Mistral-7B-Instruct-KTO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-KTO)     |  24.5  |  23.6  | 17.9 |
| Mistral Instruct 7B ORPO     | [princeton-nlp/Mistral-7B-Instruct-ORPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-ORPO)   |  24.5  |  24.9  | 20.8 |
| Mistral Instruct 7B R-DPO    | [princeton-nlp/Mistral-7B-Instruct-RDPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-RDPO)   |  27.3  |  24.5  | 16.1 |
| Mistral Instruct 7B SimPO    | [princeton-nlp/Mistral-7B-Instruct-SimPO](https://huggingface.co/princeton-nlp/Mistral-7B-Instruct-SimPO) |  32.1  |  34.8  | 21.0 |
| Llama3 Base 8B SFT           | [princeton-nlp/Llama-3-Base-8B-SFT](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT)             |   6.2  |   4.6  |  3.3 |
| Llama3 Base 8B RRHF          | [princeton-nlp/Llama-3-Base-8B-RRHF](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-RRHF)           |  10.8  |   8.1  |  6.6 |
| Llama3 Base 8B SLiC-HF       | [princeton-nlp/Llama-3-Base-8B-SLiC-HF](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SLiC-HF)     |  12.1  |  10.1  | 10.3 |
| Llama3 Base 8B DPO           | [princeton-nlp/Llama-3-Base-8B-SFT-DPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-DPO)     |  18.2  |  15.5  | 15.9 |
| Llama3 Base 8B IPO           | [princeton-nlp/Llama-3-Base-8B-SFT-IPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-IPO)     |  14.4  |  14.2  | 17.8 |
| Llama3 Base 8B CPO           | [princeton-nlp/Llama-3-Base-8B-SFT-CPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-CPO)     |  14.4  |  14.2  | 17.8 |
| Llama3 Base 8B KTO           | [princeton-nlp/Llama-3-Base-8B-SFT-KTO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-KTO)     |  14.2  |  12.4  | 12.5 |
| Llama3 Base 8B ORPO          | [princeton-nlp/Llama-3-Base-8B-SFT-ORPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-ORPO)   |  12.2  |  10.6  | 10.8 |
| Llama3 Base 8B R-DPO         | [princeton-nlp/Llama-3-Base-8B-SFT-RDPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-RDPO)   |  17.6  |  14.4  | 17.2 |
| Llama3 Base 8B SimPO         | [princeton-nlp/Llama-3-Base-8B-SFT-SimPO](https://huggingface.co/princeton-nlp/Llama-3-Base-8B-SFT-SimPO) |  22.0  |  20.3  | 23.4 |
| Llama3 Instruct 8B SFT       | [meta-llama/Meta-Llama-3-Instruct-8B](https://huggingface.co/meta-llama/Meta-Llama-3-Instruct-8B)         |  26.0  |  25.3  | 22.3 |
| Llama3 Instruct 8B RRHF      | [princeton-nlp/Llama-3-Instruct-8B-RRHF](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-RRHF) |  31.3  |  28.4  | 26.5 |
| Llama3 Instruct 8B SLiC-HF   | [princeton-nlp/Llama-3-Instruct-8B-SLiC-HF](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-SLiC-HF) |  26.9  |  27.5  | 26.2 |
| Llama3 Instruct 8B DPO       | [princeton-nlp/Llama-3-Instruct-8B-DPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-DPO)     |  40.3  |  37.9  | 32.6 |
| Llama3 Instruct 8B IPO       | [princeton-nlp/Llama-3-Instruct-8B-IPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-IPO)     |  35.6  |  35.6  | 30.5 |
| Llama3 Instruct 8B CPO       | [princeton-nlp/Llama-3-Instruct-8B-CPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-CPO)     |  33.1  |  31.8  | 26.4 |
| Llama3 Instruct 8B KTO       | [princeton-nlp/Llama-3-Instruct-8B-KTO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-KTO)     |  33.1  |  31.8  | 26.4 |
| Llama3 Instruct 8B ORPO      | [princeton-nlp/Llama-3-Instruct-8B-ORPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-ORPO)   |  28.5  |  27.4  | 25.8 |
| Llama3 Instruct 8B R-DPO     | [princeton-nlp/Llama-3-Instruct-8B-RDPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-RDPO)   |  41.1  |  37.8  | 33.1 |
| Llama3 Instruct 8B SimPO     | [princeton-nlp/Llama-3-Instruct-8B-SimPO](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-SimPO) |  44.7  |  40.5  | 33.8 |

### v0.2
We found that using a strong reward model for annotating preference optimization datasets is crucial. In this iteration, we have reannotated the dataset [princeton-nlp/llama3-ultrafeedback-armorm](https://huggingface.co/datasets/princeton-nlp/llama3-ultrafeedback-armorm) using a more powerful reward model, [RLHFlow/ArmoRM-Llama3-8B-v0.1](https://huggingface.co/RLHFlow/ArmoRM-Llama3-8B-v0.1). As a result, the v0.2 models demonstrate significantly improved performance compared to the v0.1 models.

| models                       |                                                                                                           | AE2 LC | AE2 WR |  AH  |
|------------------------------|-----------------------------------------------------------------------------------------------------------|:------:|:------:|:----:|
| Llama 3 Instruct 8B RRHF v0.2 | [princeton-nlp/Llama-3-Instruct-8B-RRHF-v2.0](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-RRHF-v0.2) |  26.0  |  25.3  | 22.3 |
| Llama 3 Instruct 8B SLiC-HF v0.2 | [princeton-nlp/Llama-3-Instruct-8B-SLiC-HF-v2.0](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-SLiC-HF-v0.2) |  37.9  |  31.6  | 28.8 |
| Llama 3 Instruct 8B DPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-DPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-DPO-v0.2) |  33.9  |  32.5  | 29.3 |
| Llama 3 Instruct 8B IPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-IPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-IPO-v0.2) |  48.2  |  47.5  | 35.2 |
| Llama 3 Instruct 8B CPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-CPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-CPO-v0.2) |  46.8  |  42.4  | 36.6 |
| Llama 3 Instruct 8B KTO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-KTO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-KTO-v0.2) |  34.1  |  36.4  | 30.9 |
| Llama 3 Instruct 8B ORPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-ORPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-ORPO-v0.2) |  34.1  |  32.1  | 27.3 |
| Llama 3 Instruct 8B R-DPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-RDPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-RDPO-v0.2) |  38.1  |  33.8  | 28.2 |
| Llama 3 Instruct 8B SimPO v0.2 | [princeton-nlp/Llama-3-Instruct-8B-SimPO-v0.2](https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-SimPO-v0.2) |  53.7  |  47.5  | 36.5 |

### Use our models for inference
Please refer to the [generate.py](generate.py) script for detailed instructions on loading the model with the appropriate chat template.

## Install Requirements

Our codebase is built upon the [alignment-handbook repo](https://github.com/huggingface/alignment-handbook). The following steps will guide you through the installation process.

First, create a Python virtual environment using e.g. Conda:
```shell
conda create -n handbook python=3.10 && conda activate handbook
```

Next, install PyTorch `v2.2.2`. Since this is hardware-dependent, we
direct you to the [PyTorch Installation Page](https://pytorch.org/get-started/locally/).

You can then install the remaining package dependencies of [alignment-handbook](https://github.com/huggingface/alignment-handbook) as follows:

```shell
git clone https://github.com/huggingface/alignment-handbook.git
cd ./alignment-handbook/
python -m pip install .
```

You will also need Flash Attention 2 installed, which can be done by running:

```shell
python -m pip install flash-attn --no-build-isolation
```

## Training Scripts

We provide four training config files for the four training setups reported in our paper. The training config is set for 8xH100 GPUs. You may need to adjust `num_processes` and `per_device_train_batch_size` based on your computation environment. 

* Mistral-Base:
```shell
ACCELERATE_LOG_LEVEL=info accelerate launch --config_file accelerate_configs/deepspeed_zero3.yaml scripts/run_simpo.py training_configs/mistral-7b-base-simpo.yaml
```
* Mistral-Instruct:
```shell
ACCELERATE_LOG_LEVEL=info accelerate launch --config_file accelerate_configs/deepspeed_zero3.yaml scripts/run_simpo.py training_configs/mistral-7b-instruct-simpo.yaml
```
* Llama3-Base:
```shell
ACCELERATE_LOG_LEVEL=info accelerate launch --config_file accelerate_configs/deepspeed_zero3.yaml scripts/run_simpo.py training_configs/llama-3-8b-base-simpo.yaml
```
* Llama3-Instruct:
```shell
ACCELERATE_LOG_LEVEL=info accelerate launch --config_file accelerate_configs/deepspeed_zero3.yaml scripts/run_simpo.py training_configs/llama-3-8b-instruct-simpo.yaml
```

## Evaluation

We follow the official implementation for evaluation on AlpacaEval 2, Arena-Hard, and MT-Bench, as follows (more details can be found under [the eval directory](https://github.com/princeton-nlp/SimPO/tree/main/eval)):

* AlpacaEval 2: Please refer to the [AlpacaEval repo](https://github.com/tatsu-lab/alpaca_eval) for evaluation.

* Arena-Hard: Please refer to to the [Arena-Hard-Auto repo](https://github.com/lm-sys/arena-hard-auto) for evaluation.

* MT-Bench: Please refer to the [FastChat repo](https://github.com/lm-sys/FastChat) for evaluation.

## Bugs or Questions?
If you have any questions related to the code or the paper, feel free to email Yu (yumeng5@virginia.edu). If you encounter any problems when using the code, or want to report a bug, feel free to open an issue! Please try to specify the problem with details so we can help you better and quicker!

## Citation
Please cite our paper if you find the repo helpful in your work:

```bibtex
@article{meng2024simpo,
  title={{SimPO}: Simple Preference Optimization with a Reference-Free Reward},
  author={Meng, Yu and Xia, Mengzhou and Chen, Danqi},
  year={2024}
}
```
