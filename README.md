# MinesweeperVariants 规则模块

## 模块简介

这是 MinesweeperVariants 项目中的规则模块，包含了扫雷游戏的所有规则实现。该模块分为几个子目录，每个子目录对应不同类型的规则：

- **Lrule/**：左线规则（雷布局规则）
- **Mrule/**：中线规则（线索与雷的交互规则）
- **Rrule/**：右线规则（线索规则）
- **rule3D/**：3D规则扩展
- **sharpRule/**：标签规则

## 规则类型说明

### 左线规则 (Lrule)

左线规则定义了地雷在题板上的布局方式。

### 中线规则 (Mrule)

中线规则定义了雷线索的显示和计算方式。

### 右线规则 (Rrule)

右线规则定义了线索的显示和计算方式。

### 3D规则 (rule3D)

三维空间的规则扩展。

### 标签规则 (sharpRule)

标签规则是一组右线规则的集合，使用标签来标识不同的规则。

## 技术实现

### 规则类结构

每个规则都实现为一个Python类，继承自相应的基类：

- 左线规则继承自 `Mines`
- 中线规则继承自 `MinesClue`
- 右线规则继承自 `Clue`

### 自动扫描机制

模块提供了自动扫描功能，能够：

- 扫描所有规则文件
- 提取规则类的文档和元信息
- 分类整理规则（L/M/R类型）
- 生成规则文档

### 主要函数

#### `extract_module_docstring(filepath)`

从Python文件提取模块和类的文档字符串。

#### `scan_module_docstrings(directory)`

扫描目录下的所有Python文件，提取规则信息。

#### `get_all_rules()`

获取所有规则的完整信息，返回按类型分类的字典。

## 使用方法

### 导入规则

```python
from minesweepervariants.impl.rule import get_all_rules

# 获取所有规则
rules = get_all_rules()
print(rules['L'])  # 左线规则
print(rules['M'])  # 中线规则
print(rules['R'])  # 右线规则
```

### 开发新规则

1. 根据规则类型选择相应的基类
2. 在对应的子目录中创建新的Python文件
3. 实现规则逻辑
4. 添加必要的文档字符串
5. 定义规则名称和参数

## 文件结构

```
rule/
├── Lrule/          # 左线规则实现
├── Mrule/          # 中线规则实现
├── Rrule/          # 右线规则实现
├── rule3D/         # 3D规则扩展
├── sharpRule/      # 标签规则
├── __init__.py     # 模块初始化和工具函数
└── README.md       # 本文档
```

## 注意事项

- 规则名称应简洁明了，通常使用字母+数字的组合
- 每个规则类必须包含完整的文档字符串
- 规则实现应遵循统一的接口规范
- 新规则需要经过测试确保正确性

## 相关文档

- [主项目](https://github.com/Minesweepervariants-Fanmade/MinesweeperVariants)
