## ADDED Requirements

### Requirement: Page tips data source
前端 SHALL 在 `frontend/src/constants/help.js` 中定义 PAGE_TIPS 常量，按页面 key 提供标题、描述和提示列表。

#### Scenario: All required pages covered
- **WHEN** 查看 PAGE_TIPS 常量
- **THEN** 包含 quote_list、project_detail、contract_detail、finance_export、reconciliation、consistency_check、profit_view 共 7 个页面

#### Scenario: Page tip structure
- **WHEN** 查看任一页面的 tip
- **THEN** 包含 title（字符串）、description（字符串）、tips（数组，最多 5 条）

### Requirement: PageHelpDrawer component
系统 SHALL 提供 PageHelpDrawer.vue 组件，从 PAGE_TIPS 读取内容并渲染帮助按钮和滑出抽屉。

#### Scenario: Page with help content
- **WHEN** PageHelpDrawer 组件接收 pageKey="quote_list"
- **THEN** 右上角渲染"? 帮助"按钮

#### Scenario: Open drawer
- **WHEN** 用户点击"? 帮助"按钮
- **THEN** 从右侧滑出抽屉（桌面 320px），显示页面标题、描述、提示列表

#### Scenario: Page without help content
- **WHEN** PageHelpDrawer 组件接收 pageKey="nonexistent"
- **THEN** 不渲染"? 帮助"按钮，静默处理

#### Scenario: Mobile full screen
- **WHEN** 在移动端打开帮助抽屉
- **THEN** 抽屉全屏展示，有明显关闭按钮

#### Scenario: Close drawer
- **WHEN** 用户点击遮罩或关闭按钮
- **THEN** 抽屉收起

### Requirement: PageHelpDrawer on required pages
所有必须覆盖的页面 SHALL 渲染 PageHelpDrawer 组件。

#### Scenario: Seven pages with help
- **WHEN** 访问报价单列表、项目详情、合同详情、财务导出、对账报表、数据核查、利润分析页面
- **THEN** 页面右上角均有"? 帮助"按钮
