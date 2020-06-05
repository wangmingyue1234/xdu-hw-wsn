# 无线传感网络课程实验

## 快速入门

该项目依赖 Python3 ，需要首先安装 Python3 和 pip

依赖第三方包 numpy 和 matplotlib 

```bash
pip3 install numpy matplotlib
```

还有一些建议的依赖，图形库默认渲染引擎我设置了 Qt5 ，依赖 PyQt5 ，为了方便阅读，我还使用了 coloredlogs 以提供彩色日志。

```bash
pip3 install pyqt5 coloredlogs
```

不过这两个不是必须的，如果没有 PyQt5 ，程序会使用默认的图形库，如果没有 coloredlogs ，程序会打印单色日志。

或者你可以简单使用以下命令安装所有依赖

```bash
pip3 install -r requirements.txt
```

依赖安装完成后只需要直接启动 `dessimation.py` 或者 `main.py` ，效果是一样的

```bash
python3 dessimation.py
```

程序会启动，按照预设的方式运行，并且实时展示生成的图像

程序运行完后，还会将日志和图像归档存储到工作路径的 `./log/` 目录下
