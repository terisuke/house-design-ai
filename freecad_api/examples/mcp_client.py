"""
FreeCAD MCP (Model Context Protocol) Client Example

This example demonstrates how to use the Model Context Protocol to interact with FreeCAD
for more efficient 3D model generation.

References:
- https://github.com/neka-nat/freecad-mcp
- https://modelcontextprotocol.io/quickstart/client#python
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any

import aiohttp


class MCPClient:
    """
    Model Context Protocol client for FreeCAD
    """

    def __init__(self, server_url: str = "http://localhost:3000"):
        """
        Initialize the MCP client

        Args:
            server_url: URL of the MCP server
        """
        self.server_url = server_url
        self.session_id = None

    async def initialize(self) -> None:
        """
        Initialize the MCP session
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "capabilities": {
                            "workspace": {
                                "workspaceFolders": True,
                                "fileOperations": {
                                    "didCreate": True,
                                    "didRename": True,
                                    "didDelete": True,
                                },
                            }
                        }
                    },
                },
            ) as response:
                result = await response.json()
                self.session_id = result.get("result", {}).get("sessionId")
                return result

    async def create_box(
        self,
        width: float,
        length: float,
        height: float,
        position: List[float] = [0, 0, 0],
        name: str = "Box",
    ) -> Dict[str, Any]:
        """
        Create a box using FreeCAD MCP

        Args:
            width: Width of the box in mm
            length: Length of the box in mm
            height: Height of the box in mm
            position: Position of the box [x, y, z] in mm
            name: Name of the box object

        Returns:
            Response from the MCP server
        """
        if not self.session_id:
            await self.initialize()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "freecad.create_box",
                        "arguments": {
                            "width": width,
                            "length": length,
                            "height": height,
                            "position": position,
                            "name": name,
                        },
                    },
                },
            ) as response:
                return await response.json()

    async def create_wall(
        self,
        start: List[float],
        end: List[float],
        height: float = 2900,  # Default 1st floor height (2900mm)
        thickness: float = 120,  # Default wall thickness (120mm)
        name: str = "Wall",
    ) -> Dict[str, Any]:
        """
        Create a wall using FreeCAD MCP

        Args:
            start: Start point of the wall [x, y, z] in mm
            end: End point of the wall [x, y, z] in mm
            height: Height of the wall in mm (default: 2900mm for 1st floor)
            thickness: Thickness of the wall in mm (default: 120mm)
            name: Name of the wall object

        Returns:
            Response from the MCP server
        """
        if not self.session_id:
            await self.initialize()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "freecad.create_wall",
                        "arguments": {
                            "start": start,
                            "end": end,
                            "height": height,
                            "thickness": thickness,
                            "name": name,
                        },
                    },
                },
            ) as response:
                return await response.json()

    async def export_model(
        self, file_path: str, format: str = "fcstd"
    ) -> Dict[str, Any]:
        """
        Export the model to a file

        Args:
            file_path: Path to save the exported file
            format: Export format (fcstd, step, stl, obj)

        Returns:
            Response from the MCP server
        """
        if not self.session_id:
            await self.initialize()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "freecad.export",
                        "arguments": {
                            "file_path": file_path,
                            "format": format,
                        },
                    },
                },
            ) as response:
                return await response.json()

    async def close(self) -> Dict[str, Any]:
        """
        Close the MCP session
        """
        if not self.session_id:
            return {"result": None}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "shutdown",
                    "params": {},
                },
            ) as response:
                return await response.json()


async def main():
    """
    Example usage of the MCP client
    """
    client = MCPClient(server_url="http://localhost:3000")
    
    try:
        await client.initialize()
        print("Session initialized")

        walls_1f = [
            await client.create_wall(
                start=[0, 0, 0],
                end=[5000, 0, 0],
                name="Wall_Front"
            ),
            await client.create_wall(
                start=[5000, 0, 0],
                end=[5000, 8000, 0],
                name="Wall_Right"
            ),
            await client.create_wall(
                start=[5000, 8000, 0],
                end=[0, 8000, 0],
                name="Wall_Back"
            ),
            await client.create_wall(
                start=[0, 8000, 0],
                end=[0, 0, 0],
                name="Wall_Left"
            ),
        ]
        print("First floor walls created")

        walls_2f = [
            await client.create_wall(
                start=[0, 0, 2900],
                end=[5000, 0, 2900],
                height=2800,  # 2nd floor height
                name="Wall_Front_2F"
            ),
            await client.create_wall(
                start=[5000, 0, 2900],
                end=[5000, 8000, 2900],
                height=2800,  # 2nd floor height
                name="Wall_Right_2F"
            ),
            await client.create_wall(
                start=[5000, 8000, 2900],
                end=[0, 8000, 2900],
                height=2800,  # 2nd floor height
                name="Wall_Back_2F"
            ),
            await client.create_wall(
                start=[0, 8000, 2900],
                end=[0, 0, 2900],
                height=2800,  # 2nd floor height
                name="Wall_Left_2F"
            ),
        ]
        print("Second floor walls created")

        export_result = await client.export_model(
            file_path="house_model.fcstd",
            format="fcstd"
        )
        print(f"Model exported: {export_result}")

        stl_result = await client.export_model(
            file_path="house_model.stl",
            format="stl"
        )
        print(f"STL exported: {stl_result}")

    finally:
        await client.close()
        print("Session closed")


if __name__ == "__main__":
    asyncio.run(main())
