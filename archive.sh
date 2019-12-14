#!/bin/bash

# 初始化工作目录
echo '初始化工作目录'
mkdir -p archive/archive/
rm -rf archive/archive/*

# 拷贝项目代码
echo '拷贝项目代码'
cp -r src/* archive/archive/
cp LICENSE archive/archive/
cp requirements.txt archive/archive/
cp README.md archive/archive/

# 拷贝报告
cp -r docs/report/ archive/archive/
mv archive/archive/report/ archive/archive/实验报告/
mv archive/archive/实验报告/report.md archive/archive/实验报告/实验报告.md
mv archive/archive/实验报告/report.pdf archive/archive/实验报告/实验报告.pdf
mv archive/archive/实验报告/report.html archive/archive/实验报告/实验报告.html
rm -rf archive/archive/实验报告/images/2.2/ archive/archive/实验报告/images/2.3.1/
rm -rf archive/archive/实验报告/images/2.3.2/ archive/archive/实验报告/images/2.3.3/

# 删除多余的文件
echo '删除多余的文件'
find archive/archive/ -name "*.pyc" -or -name "__pycache__" | xargs rm -rf
rm -rf archive/archive/log/

# 打包发布
echo '打包'
cd archive/
zip -q -r archive.zip ./archive/
