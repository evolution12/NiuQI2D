# 前后端联调待办清单

> 前端 UI 代码已全部完成，以下为需要后端 API 就绪后逐一进行的联调任务。
> 当后端完成对应模块后，在此文件中勾选并验证前端对接。

---

## 联调节点 A：生成页对接

- **后端前置**：M2-04 生成 API 路由跑通，curl 可调用
- **前端任务**：M2-05 生成页 UI 对接
- **验证项**：
  - [ ] `POST /api/generation/generate` — 文生图生成返回候选图
  - [ ] `POST /api/generation/preview` — 参数调整后实时预览
  - [ ] `POST /api/generation/variant` — 基于已有结果生成变体
  - [ ] `POST /api/generation/select` — 确认选择并保存到资产库
  - [ ] Prompt 优化器提示词增强正常工作
  - [ ] 参考图上传并正确传递到后端
  - [ ] 生成进度/状态轮询或推送正常

## 联调节点 B：资产库对接

- **后端前置**：M3-04 资产管理 API 跑通
- **前端任务**：M3-05 资产库页 UI 对接
- **验证项**：
  - [ ] `GET /api/assets` — 资产列表分页查询
  - [ ] `GET /api/assets/:id` — 单个资产详情
  - [ ] `PUT /api/assets/:id` — 更新资产信息（标签、分类）
  - [ ] `DELETE /api/assets/:id` — 删除资产
  - [ ] 资产筛选（类型、标签、日期）正确传参
  - [ ] 缩略图加载与缓存正常
  - [ ] 批量操作（批量删除、批量导出）正常

## 联调节点 C：侧边栏与项目管理对接

- **后端前置**：M4-02 项目管理 API 跑通
- **前端任务**：M4-05 侧边栏 + 项目管理对接
- **验证项**：
  - [ ] `GET /api/projects` — 项目列表加载
  - [ ] `POST /api/projects` — 创建新项目
  - [ ] `PUT /api/projects/:id` — 更新项目信息
  - [ ] `DELETE /api/projects/:id` — 删除项目
  - [ ] 项目切换后全局状态（currentProject）正确更新
  - [ ] 侧边栏项目列表实时反映增删改

## 联调节点 D：设置页对接

- **后端前置**：M5-01 API 配置持久化与测试
- **前端任务**：M5-03 设置页 UI 对接
- **验证项**：
  - [ ] `GET /api/settings` — 读取当前配置
  - [ ] `PUT /api/settings` — 保存配置变更
  - [ ] `POST /api/settings/test-image` — 图像 API 连接测试
  - [ ] `POST /api/settings/test-text` — 文本 API 连接测试
  - [ ] API Key 安全存储（不明文返回）
  - [ ] 模型列表正确展示
  - [ ] 缓存清理功能正常

## 联调节点 E：风格库对接

- **后端前置**：M4-01 风格管理 API + 参考图分析跑通
- **前端任务**：M4-04 风格库 UI 对接
- **验证项**：
  - [ ] `GET /api/styles` — 风格列表加载
  - [ ] `POST /api/styles` — 创建自定义风格
  - [ ] `PUT /api/styles/:id` — 更新风格参数
  - [ ] `DELETE /api/styles/:id` — 删除风格
  - [ ] 预设风格不可编辑/删除
  - [ ] 参考图上传与分析结果展示
  - [ ] 风格复制功能正常
  - [ ] 风格库 → 生成页风格选择联动

## 联调节点 F：导出页对接

- **后端前置**：M3-03 导出 API 跑通
- **前端任务**：M3-06 导出页 UI 对接
- **验证项**：
  - [ ] `POST /api/export/single` — 单资产导出（PNG）
  - [ ] `POST /api/export/spritesheet` — Sprite Sheet 导出
  - [ ] `POST /api/export/tileset` — Tileset 导出
  - [ ] `GET /api/export/history` — 导出历史列表
  - [ ] 导出路径选择（通过 Electron dialog）
  - [ ] 导出进度反馈正常
  - [ ] Sprite Sheet 参数（帧数、行列）正确传递
  - [ ] Tileset 拼接参数正确传递

---

## 全功能集成测试（M5-06）

全部联调节点通过后进行：

- [ ] 完整生成流程：创建项目 → 选风格 → 输入描述 → 生成 → 选图 → 入库
- [ ] 完整导出流程：选资产 → 选导出类型 → 配参数 → 导出 → 查看历史
- [ ] 项目管理流程：创建/切换/删除项目，验证数据隔离
- [ ] 风格管理流程：创建/编辑/复制/删除风格，验证生成页联动
- [ ] 设置流程：配置 API → 测试连接 → 保存 → 重启后配置保留
- [ ] 异常场景：网络断开、API 错误、文件不存在等异常提示正确
- [ ] 快捷键：Enter 发送、Escape 关闭弹窗、Ctrl+N 新建等
