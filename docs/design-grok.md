根据您的需求，我将为您设计一个基于 `cursorrules-mcp` 的系统方案，用于处理多样化的任务需求（编程、技术文档编写等），并确保跨领域规则的规范化、专业化，同时保持项目内容与风格的一致性。以下是详细的方案设计、实现思路、样例文件生成以及测试计划。

---

### 方案设计

#### 系统目标
- 支持多种任务：编程（Python、C++、Fortran、Shell 等）、技术文档编写（论文润色、基金申请、软件设计等）。
- 跨领域规则支持：提供专业化的 `cursorrules`，包括知识检索、数据接口、算法实现等。
- 内容与风格一致性：通过 Model Context Protocol (MCP) 检索和应用规则，并在 LLM 执行中保持一致性。
- 协作支持：通过 tagging 系统实现规则的关联与搜索。

#### 系统组件
1. **CursorRules 仓库**
   - 存储所有 `cursorrules`，按任务类型、语言、领域分类。
   - 使用 NoSQL 数据库（如 MongoDB）存储规则，便于处理非结构化数据。
2. **Tagging 系统**
   - 为每条规则添加标签（如 "python"、"meteorology"、"data analysis"），支持高效检索。
   - 使用 Elasticsearch 实现标签搜索功能。
3. **MCP 服务**
   - 分析任务上下文，基于标签和元数据检索适用的 `cursorrules`。
   - 与 LLM 集成，动态应用规则。
4. **LLM 引擎**
   - 使用强大的 LLM（如 GPT-4）理解任务并执行规则。
5. **一致性检查器**
   - 检查输出是否符合项目标准（如代码风格、文档格式）。
6. **API 接口**
   - 集成外部工具或服务，用于数据检索、算法调用等。

#### 工作流程
1. **任务输入**：用户通过 UI 或命令行输入任务详情。
2. **上下文分析**：MCP 服务解析任务类型、语言、领域等。
3. **规则检索**：根据标签从仓库中检索相关 `cursorrules`。
4. **任务执行**：LLM 应用规则完成任务（如编写代码或文档）。
5. **一致性检查**：确保输出符合项目标准。
6. **反馈优化**：支持用户反馈以改进规则。

---

### 具体实现

#### 技术选型
- **数据库**：MongoDB，存储 `cursorrules`。
- **搜索**：Elasticsearch，实现标签搜索。
- **LLM**：GPT-4，任务执行与规则应用。
- **版本控制**：Git，管理规则和项目输出。
- **编程语言**：Python，用于核心服务开发。

#### 实现步骤
1. **搭建 CursorRules 仓库**
   - 定义规则结构：任务类型、语言、领域、标签、具体内容。
   - 示例：`{ "task": "data analysis", "language": "python", "domain": "meteorology", "tags": ["python", "data analysis", "meteorology"], "content": "use pandas for data processing" }`。
2. **开发 Tagging 系统**
   - 集成 Elasticsearch，索引规则并支持多标签查询。
3. **实现 MCP 服务**
   - 输入任务描述，输出适用的规则集。
   - 示例：输入 "Python 气象数据分析"，返回含 "pandas"、"numpy" 的规则。
4. **集成 LLM**
   - 将规则传递给 LLM，生成代码或文档。
5. **一致性检查**
   - 使用 PEP8 检查代码风格，使用模板校验文档格式。

---

### 样例文件生成

以下是一个样例：编写一个 Python 脚本，用于分析气象数据中的温度数据。

```python
import pandas as pd
import matplotlib.pyplot as plt

def load_data(file_path):
    """加载气象数据集"""
    return pd.read_csv(file_path)

def analyze_temperature(df):
    """分析温度数据"""
    temp_mean = df['temperature'].mean()
    temp_max = df['temperature'].max()
    temp_min = df['temperature'].min()
    return {'mean': temp_mean, 'max': temp_max, 'min': temp_min}

def visualize_data(df):
    """可视化温度数据"""
    plt.plot(df['time'], df['temperature'], label='Temperature')
    plt.xlabel('Time')
    plt.ylabel('Temperature (°C)')
    plt.title('Temperature Analysis')
    plt.legend()
    plt.show()

def main():
    # 示例数据路径
    file_path = 'meteorology_data.csv'
    df = load_data(file_path)
    results = analyze_temperature(df)
    print(f"Temperature Stats: {results}")
    visualize_data(df)

if __name__ == "__main__":
    main()
```

#### 说明
- **规则应用**：使用了 "python"、"data analysis"、"meteorology" 标签对应的规则，推荐 Pandas 和 Matplotlib。
- **一致性**：代码遵循 PEP8 标准，注释清晰。

---

### 测试计划

#### 测试用例
1. **编程任务**
   - 输入：编写 C++ 程序进行地球物理数值计算。
   - 预期：生成符合项目编码标准的 C++ 代码。
2. **文档任务**
   - 输入：润色海洋学研究论文。
   - 预期：输出改进后的论文，符合期刊格式。
3. **数据检索任务**
   - 输入：从气象数据库检索并分析数据。
   - 预期：生成正确的数据处理脚本或报告。

#### 测试步骤
1. 输入测试任务到系统。
2. 检查规则检索是否准确。
3. 验证输出是否符合预期（功能、风格）。
4. 收集反馈并优化规则。

---

### 用户指南
- **系统概览**：介绍组件和工作流程。
- **任务输入**：如何清晰描述任务（示例：`python 气象数据分析`）。
- **标签使用**：如何关联和搜索 `cursorrules`。
- **一致性标准**：定义代码和文档的风格要求。
- **常见问题**：解决规则检索失败或输出不一致等问题。

通过以上设计和实现，您的 `cursorrules-mcp` 系统将能够高效处理多样化任务，并保持项目的一致性与专业性。如需进一步优化或扩展，请随时反馈！