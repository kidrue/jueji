# 爵迹 · 亚斯蓝终篇

本项目整理本地作品的写作技法，并创作亚斯蓝主线的非官方续篇。完整合集从第169回到第193回，含新增24回，正文合计80,517字。

静态阅读网站提供25回章节目录、上下一回导航、阅读进度与续读、纸页/夜间模式、字号调整、总纲、写作风格指南与Markdown下载。全部页面预生成，阅读不依赖后端、外部字体或JavaScript框架；浏览器关闭JavaScript后仍可读文与导航。

## 内容

- [完整续篇](续写/爵迹-亚斯蓝终篇.md)
- [总纲及逐回大纲](续写/终篇大纲.md)
- [人物设定与伏笔](续写/设定与伏笔.md)
- [项目写作技能](skills/lyrical-epic-fantasy-writing/SKILL.md)
- [正文验收记录](续写/验收记录.md)

## 构建与本地阅读

Python 3.10及以上即可，无额外构建依赖：

```sh
python scripts/build_site.py
python -m unittest discover -s tests -v
python -m http.server 8765 --directory docs
```

打开 `http://localhost:8765/`。网站源文件在 `site/`，静态发布目录为 `docs/`。修改章节或模板后重新构建，提交新生成的页面。

## 在线阅读与发布

仓库：<https://github.com/kidrue/jueji>。

已经发布的静态阅读网站：[打开亚斯蓝终篇](https://rawcdn.githack.com/kidrue/jueji/fd358e09daaa65523bd33e8ef89759c038a4ff24/docs/index.html)。此地址由 GitHub 提交的静态文件通过 raw.githack.com CDN 提供，固定在作品发布版本；首次访问可能显示该服务的外部内容确认页。

GitHub Pages 尚未启用。如果改用 Pages，在仓库 Settings → Pages 选择 **Deploy from a branch**，分支 **main**、目录 **/docs**。保存后 GitHub 自动发布并在后续推送时更新。启用后的默认地址为 `https://kidrue.github.io/jueji/`；站点使用相对路径，兼容该项目子目录。

CI会重新构建、逐段校验25回原文完整性、检查内部链接与下载，并验证已提交的生成文件是否与源码同步。

原作署名与来源见本地语料；本站展示本项目非官方续篇，不将其作为原作正式结局。项目写作规则固定每次创作先编写大纲，随后完成正文。

需要重新分析参考文本时，将自己的 `幻城.txt` 与 `爵迹.txt` 放到项目根目录，以GB18030读取。仓库交付完整续篇、写作资料与网站源码，构建和阅读无需这两份参考文本。
