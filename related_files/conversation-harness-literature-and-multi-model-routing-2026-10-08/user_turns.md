conversation title: 梳理Harness前沿论文



--- USER #1  10-07 09:44  len=29 ---
arixv上关于harness的前沿论文进展如何,检索梳理


--- USER #2  10-07 09:48  len=38 ---
目前我比较关注在墙钟时间-成本-通过率三方的联合优化,或者评估,寻找相关研究


--- USER #3  10-07 09:55  len=65 ---
我们的目的是开发在这三维指标上都优化的,模型无关优先,最好任务类型也无关的harness,这些是否足够,不足够的话,你是否能补充?


--- USER #4  10-07 10:00  len=105 ---
有一个重要前提,或者猜想需要你寻找可能的证明:harness设计是否默认单模型/单供应商模型?多模型/多供应商组合(先不论组合形式)能否在多数情况下比前一种情况都更占优?如果没有证明,也尽量找到置信度更高的方向


--- USER #5  10-07 10:49  len=46 ---
只要采用了存在多模型可能性的设计,那么就必须引入路由以及判断路由机制.你的对照机制设计我认可


--- USER #6  10-07 10:50  len=28 ---
现在没有完整工作给出我们想要的这个结论吗?或者部分结论?


--- USER #7  10-08 01:27  len=75 ---
仔细阅读这个:[https://arxiv.org/abs/2610.01618](https://arxiv.org/abs/2610.01618)


--- USER #8  10-08 01:34  len=92 ---
详读这一篇,不只是机制,还有具体实现,相关引文:[https://arxiv.org/abs/2601.02695](https://arxiv.org/abs/2601.02695)


--- USER #9  10-08 01:41  len=118 ---
[https://github.com/bingreeky?tab=repositories](https://github.com/bingreeky?tab=repositories)虽然仓库丢失,但是也许作者的其他仓库会有可参考?


--- USER #10  10-08 01:47  len=157 ---
同样精读[https://arxiv.org/abs/2512.18746](https://arxiv.org/abs/2512.18746)以及我找到的另一篇也许和判别有关的[https://arxiv.org/abs/2609.15309](https://arxiv.org/abs/2609.15309)
