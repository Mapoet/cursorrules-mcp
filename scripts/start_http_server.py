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
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 验证规则目录
    rules_path = Path(args.rules_dir)
    if not rules_path.exists():
        logger.warning(f"规则目录不存在: {rules_path}")
        logger.info("将在首次启动时创建规则目录和示例规则")
    
    # 显示启动信息
    logger.info("=" * 60)
    logger.info("🚀 CursorRules-MCP HTTP服务器")
    logger.info("=" * 60)
    logger.info(f"📁 规则目录: {args.rules_dir}")
    logger.info(f"🌐 服务地址: http://{args.host}:{args.port}")
    logger.info(f"📊 日志级别: {args.log_level}")
    logger.info(f"🔄 自动重载: {'启用' if args.reload else '禁用'}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📋 可用端点:")
    logger.info(f"  • 健康检查:    http://{args.host}:{args.port}/health")
    logger.info(f"  • MCP信息:     http://{args.host}:{args.port}/mcp/info") 
    logger.info(f"  • API文档:     http://{args.host}:{args.port}/docs")
    logger.info(f"  • JSON-RPC:    http://{args.host}:{args.port}/mcp/jsonrpc")
    logger.info(f"  • SSE流:       http://{args.host}:{args.port}/mcp/sse")
    logger.info("")
    logger.info("💡 按 Ctrl+C 停止服务器")
    logger.info("=" * 60)
    
    try:
        # 创建并启动服务器
        server = MCPHttpServer(
            rules_dir=args.rules_dir,
            host=args.host,
            port=args.port
        )
        
        # 如果启用了重载，使用uvicorn命令行
        if args.reload:
            import uvicorn
            uvicorn.run(
                "src.cursorrules_mcp.http_server:MCPHttpServer",
                host=args.host,
                port=args.port,
                reload=True,
                log_level=args.log_level.lower(),
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