#!/bin/bash

# 初始化工作目录
echo '初始化工作目录'
mkdir -p archive/16130120191_罗阳豪/
rm -rf archive/16130120191_罗阳豪/*

# 拷贝项目代码
echo '拷贝项目代码'
cp -r src/* archive/16130120191_罗阳豪/
cp LICENSE archive/16130120191_罗阳豪/
cp requirements.txt archive/16130120191_罗阳豪/
cp README.md archive/16130120191_罗阳豪/

# 拷贝报告
cp -r docs/report/ archive/16130120191_罗阳豪/
mv archive/16130120191_罗阳豪/report/ archive/16130120191_罗阳豪/实验报告/
mv archive/16130120191_罗阳豪/实验报告/report.md archive/16130120191_罗阳豪/实验报告/实验报告.md
mv archive/16130120191_罗阳豪/实验报告/report.pdf archive/16130120191_罗阳豪/实验报告/实验报告.pdf
mv archive/16130120191_罗阳豪/实验报告/report.html archive/16130120191_罗阳豪/实验报告/实验报告.html
rm -rf archive/16130120191_罗阳豪/实验报告/images/2.2/ archive/16130120191_罗阳豪/实验报告/images/2.3.1/
rm -rf archive/16130120191_罗阳豪/实验报告/images/2.3.2/ archive/16130120191_罗阳豪/实验报告/images/2.3.3/

# 删除多余的文件
echo '删除多余的文件'
find archive/16130120191_罗阳豪/ -name "*.pyc" -or -name "__pycache__" | xargs rm -rf
rm -rf archive/16130120191_罗阳豪/log/

# 打包发布
echo '打包'
cd archive/
#zip -q -r 16130120191_罗阳豪.zip ./16130120191_罗阳豪/
