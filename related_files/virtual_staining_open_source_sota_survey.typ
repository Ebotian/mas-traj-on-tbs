
#set page(
  paper: "a4",
  margin: (x: 20mm, y: 18mm),
  numbering: "1",
)
#set text(
  font: ("Noto Sans CJK SC", "Noto Sans"),
  size: 10pt,
  lang: "zh",
)
#set par(justify: true, leading: 0.72em)
#set table(
  stroke: 0.4pt,
  inset: 4pt,
)

#align(center)[
  #text(20pt, weight: "bold")[虚拟染色（Virtual Staining）开源前沿实现调研]
  #v(6pt)
  #text(12pt)[面向病理图像与无标记显微成像的 SOTA 方法、GitHub 实现与实验基线]
  #v(10pt)
  #text(9pt)[资料检索截止：2026-09-18]
]

#v(12pt)

= 摘要

虚拟染色（virtual staining）已从早期的单任务 GAN 图像翻译，快速演化为病理语义约束、
扩散模型（diffusion）、Diffusion Transformer（DiT）、统一多染色（multi-target / multiplex）
与病理生成基础模型（generative foundation model）并行发展的研究领域。
但“虚拟染色”并非单一任务：无标记显微图像到 H&E、H&E 到 IHC、H&E 到多重 IF、
冻结切片到 FFPE、2D 到 3D 体积虚拟染色等任务的输入信息量、配准条件、目标语义与评价方式均不同。
因此不存在可信的跨任务统一 SOTA 排名。2026 年标准化综述亦指出，
数据获取、配准、预处理、模型设置和评价协议的不一致仍显著阻碍公平比较与临床转化 @standardization2026。

本报告以“论文证据 + 官方 GitHub + 可复现性”为主线，重点调查 2024--2026 年公开实现，
并将其组织为四条技术路线：病理语义一致性、扩散/DiT、多目标统一生成、label-free / 3D。
综合来看，D-VST、PGVMS、DiffVS、StainExpert 与 PixCell 构成当前最值得直接进入实验池的
开放实现；PSPStain、TDKstain、StainPromptInversion、RegiStain、SemCG-Stain、RBDM、
HistoBIT3D 则分别提供重要的病理先验、非配对、配准鲁棒、厚组织、物理成像和 3D 路线基线。

#outline(title: [目录])

= 1. 调研范围与判定原则

== 1.1 Virtual staining 的任务边界

本报告采用较宽定义：通过学习模型从一种组织成像或染色表示生成另一种“染色表征”。
按照输入输出信息结构，可分为：

- *Label-free → stain*：如 autofluorescence、phase contrast、Mueller matrix、BIT → H&E / fluorescence。
- *Stain-to-stain*：如 H&E → IHC、H&E ↔ special stain、frozen section → FFPE。
- *Virtual multiplexing*：单一 H&E → 多 IHC marker 或 multiplex IF。
- *Volumetric virtual histology*：厚组织 / 3D label-free volume → 3D H&E-like volume。
- *Stain normalization / augmentation* 与 virtual staining 有交叉，但本报告仅在其方法直接用于跨染色生成时纳入。

2024 年综述将 virtual staining 同时涵盖 label-free staining 与 stain-to-stain transformation @latonen2024；
2026 年系统综述则进一步将数字染色相关任务拆分为 stain normalization、augmentation、
virtual staining、stain transformation 与 hybrid approaches @digitalstain2026。

== 1.2 “开源 SOTA”不等于单一排行榜

本报告不把论文作者声称的 “state of the art” 直接视为跨领域第一名，而按三层证据判断：

1. *论文前沿性*：是否发表于近年高质量会议/期刊，方法是否代表当前研究方向。
2. *开源完整度*：是否提供训练代码、推理代码、配置、权重、数据说明、evaluation protocol。
3. *可比较性*：是否在相同数据、相同配准条件、相同 split 和相同评价定义下比较。

H&E→IHC benchmark 已显示：不同方法在 PSNR/SSIM、FID/LPIPS 与病理相关指标之间可能出现明显冲突，
故仅凭单一传统图像指标无法判断临床意义上的优劣 @benchmark2025。

= 2. 2024--2026 技术演化主线

== 2.1 从像素翻译到病理语义约束

早期 virtual staining 常直接优化 $L_1$、$L_2$、SSIM 或 adversarial loss。
但病理图像与普通风格迁移不同：微小结构改变可能对应诊断语义改变。
因此近期方法显式引入 nuclei、membrane、protein-expression distribution、
pathology foundation model feature 或 pathology classifier 作为约束。

代表工作：

- *PSPStain*：pathological semantics-preserving H&E→IHC；其作者仓库明确将后续完整版本指向 PGVMS。
- *TDKstain*：针对 HER2 scoring 注入 nuclei distribution 与 membrane intensity 领域知识 @tdkstain2024。
- *ODA-GAN*：利用 pathology foundation model、orthogonal feature decoupling 与 weak supervision，
  解决 unpaired H&E→IHC 的 staining-related / unrelated feature 分离 @odagan2025。
- *PGVMS*：将 pathological VLM prompt、protein-aware learning 与 prototype-consistent learning
  合并为统一 multi-IHC 模型 @pgvms2026。

== 2.2 Diffusion / DiT 成为主流前沿

2024 年 PST-Diff 已将 diffusion 引入高一致性 stain transfer，通过 AAM、latent transfer 与结构约束保持病理一致性
@pstdiff2024。2025--2026 年进一步出现：

- *D-VST*：Diffusion Transformer + pathology/tone disentanglement + WSI adaptive sampling @dvst2025。
- *DiffVS*：marker-wise conditioned latent diffusion，并使用 Diffusion-FT 压缩至 one-step virtual staining。
- *StainExpert*：multi-expert multimodal diffusion，支持一源多目标 stain translation @stainexpert2026。
- *RBDM*：将 regulated bridge diffusion 用于 16-channel Mueller Matrix → H&E / fluorescence @rbdm2025。

趋势由“生成一张视觉上像目标染色的图”转向：

$ G(x, c) -> y_c $

其中条件 $c$ 可以表示 stain、marker、text prompt、pathology semantics 或 tone。

== 2.3 统一多染色与基础模型化

Virtual multiplexing 正从“每个 marker 一个网络”转向统一条件生成：

$ G(x, m_i) -> y_(m_i), quad m_i in M $

其中 $M$ 可包含 HER2、ER、PR、Ki67、multiplex IF markers 等。

- *PGVMS*：以 prompt 统一多 IHC。
- *DiffVS*：以 marker token 统一多 marker。
- *StainExpert*：以 mixture-of-experts / multi-objective 处理多染色域。
- *PixCell*：更进一步，从“专用 virtual staining model”转向“病理生成 foundation model + LoRA / flow matching adaptation”。
  PixCell 在约 69,184 张 WSI、30.8M patches 上训练，virtual staining 作为下游生成任务之一 @pixcell2025。

== 2.4 Label-free、厚组织与 3D 路线独立发展

这一分支不能与 H&E→IHC 直接做数值排名，因为输入信息和采集物理完全不同。

- *RegiStain*：autofluorescence → H&E，并联合训练 registration network 与 staining network，
  解决配准误差与 autopsy tissue artifact @registain2024。
- *SemCG-Stain*：light-sheet fluorescence thick tissue → H&E；
  用 pathology foundation feature 做 semantic contrastive guidance @semcg2025。
- *RBDM*：polarimetric Mueller Matrix → H&E / fluorescence；
  MICCAI 2025 工作使用 18,000 paired images，并公开代码 @rbdm2025。
- *HistoBIT3D*：phase-contrast Back-illumination Interference Tomography → 3D H&E；
  引入 voxel-wise paired fluorescence nuclei 作为结构真实性验证依据 @histobit2026。

= 3. 开源实现总表

#text(8.2pt)[
#table(
  columns: (1.25fr, 1.15fr, 1.65fr, 0.9fr, 1.35fr),
  [*项目*], [*主要任务*], [*核心方法*], [*开源状态*], [*建议用途*],

  [D-VST], [HE→IHC / FFPE→HE / HE→mIHC],
  [DiT；pathology/tone disentanglement；WSI adaptive sampling],
  [完整度高],
  [cross-dye / WSI diffusion 主实验],

  [PGVMS], [HE→HER2/ER/PR/Ki67],
  [prompt-guided unified model；PALS；PCLS；CONCH],
  [完整度高],
  [统一 multi-IHC 主实验],

  [DiffVS], [HE→multiplex IF / stain],
  [marker-conditioned latent diffusion；Diffusion-FT one-step],
  [完整度高],
  [多 marker 条件生成主实验],

  [StainExpert], [source→multi-target stains],
  [multi-expert multimodal diffusion；distillation],
  [完整度高],
  [多目标、多域 diffusion 主实验],

  [PixCell], [HE→IHC；通用 pathology generation],
  [pan-cancer DiT foundation model；LoRA；flow-matching MLP],
  [完整度高],
  [foundation-model adaptation 路线],

  [PSPStain], [HE→IHC],
  [pathological semantics-preserving learning],
  [完整],
  [病理语义 baseline],

  [TDKstain], [HE→HER2 IHC],
  [nuclei + membrane task knowledge],
  [完整],
  [HER2 task-specific baseline],

  [StainPromptInversion], [unpaired multi-domain stain transfer],
  [dual-path inversion；visual prompt optimization],
  [较完整],
  [unpaired / training-light baseline],

  [ODA-GAN], [unpaired HE→IHC],
  [orthogonal decoupling；DPNCE；MDA],
  [仅核心代码],
  [论文前沿；暂不宜作为主复现 baseline],

  [RegiStain], [autofluorescence→HE],
  [joint registration + structurally-conditioned GAN],
  [完整；含权重/示例],
  [registration-aware label-free baseline],

  [SemCG-Stain], [thick-tissue fluorescence→HE],
  [semantic contrastive guidance；pathology-aware discriminator],
  [代码可用；数据说明待完善],
  [section-free thick tissue],

  [RBDM], [Mueller Matrix→HE/fluorescence],
  [regulated bridge diffusion],
  [代码+权重],
  [physical imaging→stain diffusion],

  [HistoBIT3D], [3D BIT→3D HE],
  [UVCGANv2；multiscale consistency；AdaIN style reuse],
  [代码已开；dataset 仍在发布过程中],
  [3D / slide-free 前沿],

  [virtual_stain_flow], [label-free microscopy→fluorescence],
  [UNet / wGAN-GP / ConvNeXt-UNet；MLflow],
  [工程完整度很高],
  [统一研究 harness / baseline infrastructure],
)
]

= 4. 重点开源项目审查

== 4.1 D-VST

*论文*：NeurIPS 2025 @dvst2025  
*仓库*：#link("https://github.com/yangshurong/D-VST")[yangshurong/D-VST]

核心问题是 *pathology leakage*：生成模型将非病理区域错误染成阳性，或反之。
D-VST 将 pathology condition 与 tone condition 分开编码，并采用 two-stage curriculum learning。
此外，它针对 billion-pixel WSI 设计 frequency-aware adaptive patch sampling。

开源内容包括训练、推理、YAML 配置、multi-GPU/DeepSpeed 使用方式以及 HE2IHC、
FFPE2HE、HE2mIHC 权重。官方 README 明确要求 paired source/target patches，
因此其“强效果”建立在配对数据假设上。

*适合研究的问题*：
- pathology/tone disentanglement 是否真实降低 semantic leakage；
- patch-level 指标与 WSI-level 一致性之间的差异；
- WSI adaptive sampling 是否改变 rare-positive regions 的覆盖率；
- DiT 相比 GAN / latent diffusion 的真实收益是否来自架构还是预训练规模。

== 4.2 PGVMS

*论文*：IEEE TMI 2026 @pgvms2026  
*仓库*：#link("https://github.com/ccitachi/PGVMS")[ccitachi/PGVMS]

PGVMS 是 PSPStain 的后续统一版本。其三部分核心设计分别针对：

- semantic guidance：pathological VLM adaptive prompt；
- protein-expression consistency：Protein-Aware Learning Strategy (PALS)；
- spatial misalignment：Prototype-Consistent Learning Strategy (PCLS)。

它支持 MIST / IHC4BC，并将 HER2、ER、PR、Ki67 混合在统一数据目录中训练。
仓库给出训练、测试和 checkpoint 下载入口。

*适合研究的问题*：
- prompt 是否真正学习 stain-specific semantics，还是仅作为 domain token；
- PALS 对 OD/DAB distribution 的收益是否会牺牲局部 morphology；
- PCLS 对 adjacent-section misalignment 的鲁棒边界；
- single unified model 与 per-marker expert model 的容量冲突。

== 4.3 DiffVS

*论文*：AAAI 2026  
*仓库*：#link("https://github.com/hvcl/DiffVS")[hvcl/DiffVS]

DiffVS 的核心是 marker-wise conditioned diffusion。
Stage 1 为 Marigold-style paired latent diffusion；
Stage 2 使用 Diffusion-FT 将模型压缩为 one-step inference。

公开实现覆盖 ORION-CRC 与 HEMIT，并给出 HEMIT paper-test split、
sliding-window inference 以及明确的数据格式，是当前较少见的 protocol-level 开源实现。

*适合研究的问题*：
- one-step distillation 对 marker specificity 的损失；
- 多 marker shared backbone 是否存在 negative transfer；
- marker token 的表示几何是否与蛋白共表达结构相关；
- ORION-CRC 上的 multiplex IF 是否能作为“同一组织、多 marker”更严格的评价场。

== 4.4 StainExpert

*论文*：IEEE TMI, 2026 May issue；DOI 10.1109/TMI.2025.3641562 @stainexpert2026  
*仓库*：#link("https://github.com/Rowerliu/StainExpert")[Rowerliu/StainExpert]

StainExpert 采用 multi-expert multimodal diffusion：
多个 specialist networks 协同学习共享染色规律，同时保持 stain-specific expertise。
模型还结合 textual guidance、visual feature、parameter-efficient design 与 model distillation。

官方仓库目前包含 `train.py`、`test.py`、dataset/util 结构，
并示例设置 `experts=4`, `topk=2`，适合作为 mixture-of-experts 路线代表。

*适合研究的问题*：
- MoE routing 与 stain semantics 是否存在可解释对应；
- expert collapse / load imbalance；
- unified multi-target 与 PGVMS / DiffVS 的参数效率比较；
- distillation 后速度、结构一致性和稀有 marker fidelity 的 Pareto 曲线。

== 4.5 PixCell

*论文*：generative foundation model for digital histopathology @pixcell2025  
*仓库*：#link("https://github.com/cvlab-stonybrook/PixCell")[cvlab-stonybrook/PixCell]

PixCell 不是单纯 virtual staining network，而是 pan-cancer generative foundation model。
其训练规模约为 69,184 WSIs / 30.8M 1024×1024 patches；
生成模型以 UNI2-h embedding 提供 self-supervised conditioning。
Virtual staining 下游通过 PixCell-1024 LoRA + flow-matching MLP 实现，
目前公开 MIST 的 HER2/ER/PR/Ki67 与 HER2Match 相关模型。

这代表了一个重要范式：

$ "task-specific generator" -> "generative pathology prior + parameter-efficient adaptation" $

*适合研究的问题*：
- pathology prior 是否能减少小数据 stain task 的样本复杂度；
- foundation prior 会否 hallucinate plausible-but-false pathology；
- LoRA/MLP adaptation 与 full fine-tuning 的病理一致性差异；
- foundation representation 对跨医院、跨 scanner domain shift 的作用。

== 4.6 ODA-GAN：论文强，但当前不应标成“完整可复现”

*论文*：CVPR 2025 @odagan2025  
*仓库*：#link("https://github.com/ittong/ODA-GAN")[ittong/ODA-GAN]

ODA-GAN 通过 pathology foundation model 生成弱监督信号，
并使用 Orthogonal MLP 将 staining-related 与 staining-unrelated feature 解耦，
再通过 Dual-stream PatchNCE 与 Multi-layer Domain Alignment 提高真实性与一致性。

但截至本次检索，官方 GitHub README 明确说明：
当前仅发布 selected core implementations，完整 training/inference code “will be released in a future update”。
故它应被视为 *论文方法前沿*，而不是当前最适合作为统一实验 baseline 的工程实现。

= 5. Label-free / physical imaging / 3D 开源路线

== 5.1 RegiStain

Nature Communications 2024 的 autopsy virtual staining 使用 autofluorescence 作为输入，
并联合训练 image-registration network 与 virtual-staining network @registain2024。
论文使用超过 16,000 paired microscopic images，目标之一是减轻 autolysis 与配准误差。
官方仓库提供训练/测试代码、Zenodo 权重与示例图像。

其意义不只是“一个旧 GAN”：
*registration error 本身应成为模型的一部分，而非被假设为数据预处理已经完全解决。*

== 5.2 SemCG-Stain

MICCAI 2025 @semcg2025  
#link("https://github.com/commashy/SemCG-Stain")[commashy/SemCG-Stain]

输入为 thick tissue 的 fluorescence light-sheet microscopy，
输出 virtual H&E。
其 semantic contrastive guidance 使用 pathology foundation model feature，
并配合 subtype-aware discriminator。
代码已公开，但 README 对 dataset/preprocessing 仍写有后续更新提示，因此复现实验需额外阅读论文并重构数据流程。

== 5.3 RBDM

MICCAI 2025 @rbdm2025  
#link("https://github.com/xiaoyu-z/RBDM")[xiaoyu-z/RBDM]

RBDM 把 16-channel Mueller Matrix polarization imaging 映射到 H&E / fluorescence，
通过 regulated Brownian-bridge-like diffusion 约束起点和路径。
论文报告数据集初版含约 18,000 paired patches，并公开代码。

该路线值得单列，因为它研究的是：

$ "physical optical measurement" -> "pathologist-readable stain" $

而非单纯从一类 RGB stain 到另一类 RGB stain。

== 5.4 HistoBIT3D

2026 年 HistoBIT3D 将 phase-contrast Back-illumination Interference Tomography
映射为 3D virtual H&E @histobit2026。
其一个关键创新是构建 voxel-wise paired BIT / fluorescence nuclei dataset，
从而可用真实 nuclei distribution 评价虚拟染色是否保持 3D 结构，而不仅用 FID/SSIM。

官方代码已公开，但 README 同时说明完整 dataset 正在继续准备公开。
因此它适合作为 *研究方向和模型结构前沿*，
但目前尚不适合作为最省成本的 reproduction starting point。

= 6. Benchmark 与评价体系

== 6.1 不能只用 PSNR / SSIM

H&E→IHC benchmark @benchmark2025 在 MIST 上统一重训代表模型，
并同时比较：

$ E = E_"pixel" + E_"perceptual" + E_"stain" $

其中包括：
- SSIM / PSNR：像素/结构相似；
- FID / LPIPS：perceptual distribution；
- JSD of DAB intensity：IHC 染色分布。

研究表明这些指标可能相互矛盾：更好的 FID/LPIPS/病理 stain distribution
不必然对应更高的 PSNR/SSIM。
原因之一是 H&E/IHC 常来自 adjacent sections，像素级严格对应本就不成立。

== 6.2 建议统一评价空间

建议后续实验采用正交评价分解：

$
E = (
  E_"pixel",
  E_"perceptual",
  E_"morphology",
  E_"marker",
  E_"downstream",
  E_"robustness"
)
$

具体可定义：

- $E_"pixel"$：PSNR、SSIM、MAE，仅用于高度配准 pair。
- $E_"perceptual"$：LPIPS、FID/KID。
- $E_"morphology"$：nuclei count、boundary F1、cell topology、gland structure。
- $E_"marker"$：DAB/OD distribution、marker-positive ratio、spatial protein pattern。
- $E_"downstream"$：HER2 scoring、ER/PR/Ki67 classification、segmentation、cell typing。
- $E_"robustness"$：scanner/site/tissue-type shift、registration perturbation、stain intensity shift。

并同时记录不确定性：

$ (mu, sigma, "CI", "seed", "split") $

而非只报告最佳单次结果。

= 7. 建议构建的统一开源实验池

== 7.1 第一层：共同 baseline

建议至少保留：

- Pix2Pix / Pix2PixHD
- CUT / PatchNCE 系
- ASP
- PSPStain
- TDKstain（HER2 specific）

目标是覆盖：

$ "plain image translation" -> "contrastive translation" -> "pathology-aware GAN" $

== 7.2 第二层：2025--2026 frontier

核心实验组：

- PGVMS：semantic unified multi-IHC
- D-VST：DiT / pathology-tone disentanglement / WSI
- DiffVS：marker-conditioned multiplex diffusion
- StainExpert：multi-expert unified diffusion
- PixCell：foundation model + PEFT

这五个实现对应五种不同建模假设，不应提前按单一指标筛掉任何一路线。

== 7.3 第三层：unpaired / registration / physical imaging

独立实验组：

- StainPromptInversion：unpaired, prompt inversion
- RegiStain：joint registration
- SemCG-Stain：thick tissue
- RBDM：polarimetric imaging
- HistoBIT3D：3D phase tomography

注意这些方法的数据生成机制差异极大，
应比较“研究思想与模块”，而非跨数据直接比较最终 PSNR/FID。

== 7.4 实验基础设施

#link("https://github.com/WayScience/virtual_stain_flow")[WayScience/virtual_stain_flow]
值得作为工程参考。它将 dataset、transform、model、trainer、logging 拆分，
支持 UNet / wGAN-GP / ConvNeXt-UNet 与 MLflow，
比单个论文仓库更接近可复用的 virtual-staining research harness。

可将前沿模型适配为统一接口：

```text
DatasetSpec
  -> Pairing / Registration policy
  -> Patch sampler
  -> ModelAdapter
  -> TrainProtocol
  -> InferenceProtocol
  -> MetricBundle
  -> Artifact / Checkpoint / Seed record
```

从研究工程角度，这比直接 fork 每篇论文并在各自脚本中比较结果更可靠。

= 8. 推荐的研究问题

基于当前公开前沿，以下问题比“再换一个 generator backbone”更有研究价值：

== 8.1 信息可识别性（identifiability）

对于 H&E→IHC：

$ p(y_"IHC" | x_"HE") $

是否本质上是多模态分布，而非确定映射？
若 H&E 中不存在足够的分子信息，则模型可能只能学习 population prior。
应区分：

$ "recoverable signal" $
与
$ "plausible hallucination" $。

== 8.2 配准误差与 supervision noise

将真实 target 表示为：

$ y = T_delta(y^*) + epsilon $

其中 $T_delta$ 是未知局部 deformation。
则普通 $L_1/L_2$ 实际会把 registration error 当作 prediction error。
RegiStain、PGVMS/PCLS 等方法说明：
registration uncertainty 应被显式建模。

== 8.3 多 marker 共享表示的正负迁移

若统一模型共享参数 $theta_s$，各 marker 有条件参数 $theta_i$：

$ L = sum_i lambda_i L_i(theta_s, theta_i) $

需要研究不同 $nabla L_i$ 间的夹角：

$ cos(g_i, g_j) = (g_i dot g_j) / (norm(g_i) norm(g_j)) $

以判断 marker 间是 synergistic transfer 还是 gradient conflict。
这对 PGVMS、DiffVS、StainExpert 特别关键。

== 8.4 生成基础模型的病理先验究竟帮助还是污染

PixCell 路线引入强先验：

$ p_theta(y | z_"pathology") $

可能改善 sample efficiency，也可能在输入证据不足时生成“高可信度但错误”的典型结构。
因此应把 hallucination / evidence consistency 纳入评价，而非只看 realism。

== 8.5 WSI-level consistency

Patch generator 的局部最优：

$ G(x_k) -> y_k $

不保证拼接后的 WSI 在颜色、marker density、rare lesion continuity 上一致。
D-VST 的 WSI sampling 是一个起点，但仍应单列：

- seam consistency；
- global stain distribution；
- rare-positive region recall；
- cross-scale pathology consistency。

= 9. 结论

截至 2026-09，virtual staining 的开源前沿可概括为：

$
"GAN image translation"
-> "pathology-aware constraints"
-> "diffusion / DiT"
-> "unified multi-stain"
-> "generative foundation model"
$

同时，label-free optical imaging 与 3D virtual histology 正形成另一条独立主线。

若目标是建立一个面向真实研究的开源 SOTA 实验池，
最有价值的核心集合不是一个“冠军模型”，而是：

$
{ "PGVMS", "D-VST", "DiffVS", "StainExpert", "PixCell" }
$

并以：

$
{ "PSPStain", "TDKstain", "StainPromptInversion", "RegiStain" }
$

作为关键结构性 baseline，
再按具体采集模态引入 SemCG-Stain、RBDM、HistoBIT3D。

当前领域最大的空缺并非“缺少更强生成器”，
而是缺少统一的 data contract、registration contract、evaluation space、
WSI protocol、uncertainty reporting 和跨站点验证。
因此，一个高价值后续工程方向是：
*把这些开源方法适配进统一 research harness，并在同一数据构造与评价契约下重跑。*

= 参考文献

#bibliography("virtual_staining_refs.bib", style: "ieee")
