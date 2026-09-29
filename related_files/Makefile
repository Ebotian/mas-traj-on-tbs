# Typst 文档编译
#
#   make                编译全部 .typ，产物写入 pdf/
#   make <文件名>       只编译一个，不带 .typ 后缀，例如
#                         make ada-engineering-plan
#                         make virtual_staining_open_source_sota_survey
#   make list           列出全部源文件
#   make clean          删除 pdf/ 及其中所有产物
#
# 源码目录只放 .typ / .bib，产物统一进 pdf/。
# 依赖取自 wildcard，新增 .typ 或 .bib 后无需改本文件。
# 任一 .bib 变更会触发全部文档重编译：目前只有两份文档用参考文献，
# 用这个粗粒度依赖换 Makefile 的简单可靠。

TYPST ?= typst
OUT   := pdf
SRC   := $(wildcard *.typ)
BIB   := $(wildcard *.bib)
PDF   := $(patsubst %.typ,$(OUT)/%.pdf,$(SRC))

.PHONY: all list clean

all: $(PDF)

$(OUT)/%.pdf: %.typ $(BIB) | $(OUT)
	$(TYPST) compile "$<" "$@"

# 支持 make <文件名>（不带 .typ 后缀）编译单个文档
%: %.typ | $(OUT)
	$(TYPST) compile "$<" "$(OUT)/$@.pdf"

$(OUT):
	mkdir -p $(OUT)

list:
	@ls -1 *.typ

clean:
	rm -rf $(OUT)
