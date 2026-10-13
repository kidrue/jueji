# 爵迹 · 原文与亚斯蓝终篇

本项目整理本地作品的写作技法，并创作亚斯蓝主线的非官方续篇。完整合集从第169回到第193回，含新增24回，正文合计80,517字。

静态阅读网站同时提供郭敬明《爵迹》的本地原文与本项目非官方续篇。原文目录含157个现有标题及《致爵迹读者》附记，共158篇；文本收录至《银色琥珀》。文件中的部分标题缺失、编号重复或标题粘连，网站按原文件顺序分篇，保留全部文字。原文与续篇有独立目录、翻页和阅读进度，共享纸页/夜间模式与字号设置。

原文全文TXT、非官方续篇Markdown、大纲与完整写作技能均可下载。全部187个页面预生成，阅读不依赖后端、外部字体或JavaScript框架；浏览器关闭JavaScript后仍可读文与导航。

## 内容

- [爵迹原文页面模板](site/templates/original.html)
- [爵迹原文UTF-8文本](site/texts/jueji.txt)
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

打开 `http://localhost:8765/` 阅读续篇，`http://localhost:8765/original.html` 阅读原文。网站源文件在 `site/`，构建产物在 `docs/`；产物由Actions生成并发布，无需提交。修改原文、续篇或模板后提交源码即可自动更新网站。

## 在线阅读与发布

仓库：<https://github.com/kidrue/jueji>。

网站采用 **GitHub Actions 构建 + GitHub Pages 静态托管**。部署工作流为 [deploy-pages.yml](.github/workflows/deploy-pages.yml)：推送main或手动运行时，构建页面、运行完整性与链接检查，随后上传docs构建产物并部署到github-pages环境。

首次启用：仓库 [Settings → Pages](https://github.com/kidrue/jueji/settings/pages) → Build and deployment → Source 选择 **GitHub Actions**。随后在Actions中运行 **Deploy reading site to GitHub Pages**。无需配置分支目录，也无需额外服务。

部署成功后的地址：原文 `https://kidrue.github.io/jueji/original.html`；续篇 `https://kidrue.github.io/jueji/`。是否已上线以Actions的部署结果为准。站点使用相对路径，兼容项目子目录。

此前续篇发布版本的[静态CDN地址](https://rawcdn.githack.com/kidrue/jueji/fd358e09daaa65523bd33e8ef89759c038a4ff24/docs/index.html)仍可访问；该固定版本不包含此次新增原文。

CI会核对原文全部字符的阅读顺序、全文下载、25回续篇逐段完整性、内部链接与跨系统构建的一致性。

原文作者为郭敬明，文本及原文件来源说明保存在原文首页的“书前信息与文本说明”。续篇注明为本项目非官方创作。项目写作规则固定每次创作先编写大纲，随后完成正文。

`site/texts/jueji.txt`由当前目录的`爵迹.txt`按GB18030解码后无损转为UTF-8，是原文网站的构建输入。原始GB18030文件留在本地；仓库中的UTF-8版本保留其全部文字。重新进行两部作品的风格分析时，仍可使用本地`幻城.txt`与`爵迹.txt`。
