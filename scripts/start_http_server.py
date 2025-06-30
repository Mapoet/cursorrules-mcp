#!/usr/bin/env python3
"""
CursorRules-MCP HTTP服务器启动脚本
支持通过HTTP/SSE协议提供MCP服务

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cursorrules_mcp.http_server import MCPHttpServer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="CursorRules-MCP HTTP服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认配置启动服务器
  python scripts/start_http_server.py
  
  # 指定端口和主机
  python scripts/start_http_server.py --host 0.0.0.0 --port 8080
  
  # 指定自定义规则目录
  python scripts/start_http_server.py --rules-dir /path/to/rules
  
  # 使用多个工作进程（生产环境推荐）
  python scripts/start_http_server.py --workers 4
  
API端点:
  - GET  /health              - 健康检查
  - GET  /mcp/info            - MCP服务信息
  - POST /mcp/connect         - 建立MCP连接
  - POST /mcp/jsonrpc         - JSON-RPC请求处理
  - GET  /mcp/sse             - Server-Sent Events流
  - GET  /docs                - API文档（Swagger UI）
        """
    )
    
    parser.add_argument(
        "--rules-dir",
        default="data/rules",
        help="规则目录路径 (默认: data/rules)"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="服务器主机地址 (默认: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用自动重载（开发模式）"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数量 (默认: 1，适用于生产环境多核CPU)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default="configs/cursorrules.yaml",
        help="主配置文件路径 (默认: configs/cursorrules.yaml)"
    )
    
    args = parser.parse_args()
    
    # 加载主配置
    from src.cursorrules_mcp.config import get_config
    config = get_config(args.config)

    # 路径参数优先用 config 文件
    rules_path = Path(config.rules_dir)
    templates_path = Path(getattr(config, 'templates_dir', 'data/templates'))
    log_level = getattr(config.server, 'log_level', args.log_level)
    host = getattr(config.server, 'host', args.host)
    port = getattr(config.server, 'port', args.port)
    workers = getattr(config.server, 'workers', args.workers)
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    # 验证规则目录
    if not rules_path.exists():
        logger.warning(f"规则目录不存在: {rules_path}")
        logger.info("将在首次启动时创建规则目录和示例规则")
    
    # 显示启动信息
    logger.info("=" * 60)
    logger.info("🚀 CursorRules-MCP HTTP服务器")
    logger.info("=" * 60)
    logger.info(f"📁 规则目录: {rules_path}")
    logger.info(f"📁 模板目录: {templates_path}")
    logger.info(f"🌐 服务地址: http://{host}:{port}")
    logger.info(f"📊 日志级别: {log_level}")
    logger.info(f"🔄 自动重载: {'启用' if args.reload else '禁用'}")
    logger.info(f"👥 工作进程: {workers}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📋 可用端点:")
    logger.info(f"  • 健康检查:    http://{host}:{port}/health")
    logger.info(f"  • MCP信息:     http://{host}:{port}/mcp/info") 
    logger.info(f"  • API文档:     http://{host}:{port}/docs")
    logger.info(f"  • JSON-RPC:    http://{host}:{port}/mcp/jsonrpc")
    logger.info(f"  • SSE流:       http://{host}:{port}/mcp/sse")
    logger.info("")
    logger.info("💡 按 Ctrl+C 停止服务器")
    logger.info("=" * 60)
    
    try:
        # 创建并启动服务器
        server = MCPHttpServer(
            rules_dir=str(rules_path),
            host=host,
            port=port,
            workers=workers
        )
        
        # 设置环境变量，供多进程模式使用
        import os
        os.environ["CURSORRULES_RULES_DIR"] = str(rules_path)
        os.environ["CURSORRULES_TEMPLATES_DIR"] = str(templates_path)
        os.environ["CURSORRULES_HOST"] = host
        os.environ["CURSORRULES_PORT"] = str(port)
        os.environ["CURSORRULES_WORKERS"] = str(workers)
        
        # 如果启用了重载，使用uvicorn命令行
        if args.reload:
            import uvicorn
            # 注意：uvicorn的reload模式不支持多workers
            if workers > 1:
                logger.warning("⚠️  reload模式不支持多workers，将使用单进程模式")
            uvicorn.run(
                "src.cursorrules_mcp.http_server:MCPHttpServer",
                host=host,
                port=port,
                reload=True,
                log_level=log_level.lower(),
                factory=True
            )
        else:
            server.run()
            
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 