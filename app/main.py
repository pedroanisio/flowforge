from fastapi import FastAPI, Request, Form, HTTPException, File, UploadFile, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Dict, Any, Optional
from datetime import timedelta
import os
import json
import time
import uuid
import tempfile
import aiofiles
from pathlib import Path

from .core.plugin_manager import PluginManager
from .core.chain_manager import ChainManager
from .core.config import settings
from .core.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    optional_auth, Token, User
)
from .core.logging_config import logger
from .models.plugin import PluginInput
from .models.response import PluginListResponse, PluginExecutionResponse
from .models.chain import ChainDefinition, ChainExecutionResult

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

# Initialize FastAPI app
app = FastAPI(
    title="Neural Plugin System with Chain Builder",
    description="A FastAPI + Pydantic web application with dynamic plugin system and visual chain builder",
    version="2.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
plugin_manager = PluginManager()
chain_manager = ChainManager(plugin_manager)

# Log application startup
logger.info(
    f"Starting {app.title} v{app.version}",
    extra={
        "environment": settings.environment,
        "auth_enabled": settings.enable_auth,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "max_upload_mb": settings.max_upload_size_mb
    }
)

# Setup templates and static files
templates = Jinja2Templates(directory="app/templates")

# Add custom Jinja2 filters
def tojsonpretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False)

templates.env.filters['tojsonpretty'] = tojsonpretty

app.mount("/static", StaticFiles(directory="app/static"), name="static")


async def _stream_upload_to_temp(upload_file: UploadFile, max_size_bytes: Optional[int] = None) -> str:
    """
    Stream uploaded file to temporary location without loading into memory

    Args:
        upload_file: The uploaded file
        max_size_bytes: Maximum file size in bytes (defaults to settings.max_upload_size_bytes)

    Raises:
        HTTPException: If file exceeds maximum size
        RuntimeError: If file streaming fails
    """
    if max_size_bytes is None:
        max_size_bytes = settings.max_upload_size_bytes

    temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{upload_file.filename}")

    try:
        total_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as temp_file:
            while chunk := await upload_file.read(8192):  # 8KB chunks
                total_size += len(chunk)

                # Check file size limit
                if total_size > max_size_bytes:
                    # Clean up partial file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds maximum allowed size of {settings.max_upload_size_mb}MB"
                    )

                await temp_file.write(chunk)

        logger.info(f"File uploaded successfully: {upload_file.filename} ({total_size} bytes)")
        return temp_file_path
    except HTTPException:
        raise
    except Exception as e:
        # Clean up partial file if error occurs
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        logger.error(f"Failed to stream upload: {e}")
        raise RuntimeError(f"Failed to stream upload to temporary file: {e}")


def cleanup_downloads_directory(max_age_hours: int = 24):
    """Clean up old files from downloads directory"""
    downloads_dir = Path("/app/data/downloads")
    if not downloads_dir.exists():
        return {"cleaned": 0, "error": "Downloads directory does not exist"}
    
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        for file_path in downloads_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    cleaned_count += 1
        
        return {"cleaned": cleaned_count, "max_age_hours": max_age_hours}
    except Exception as e:
        return {"cleaned": 0, "error": str(e)}


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")


# ========== AUTHENTICATION ENDPOINTS ==========

@app.post("/token", response_model=Token)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login endpoint

    Usage:
        curl -X POST http://localhost:8000/token \\
             -d "username=admin&password=secret"
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information (requires authentication if enabled)"""
    return current_user


@app.get("/auth/status")
async def auth_status():
    """Check authentication status and configuration"""
    return {
        "auth_enabled": settings.enable_auth,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "environment": settings.environment
    }


# ========== WEB INTERFACE ROUTES ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage showing available plugins"""
    plugins = plugin_manager.get_all_plugins()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "plugins": plugins,
        "auth_enabled": settings.enable_auth
    })


@app.get("/how-to", response_class=HTMLResponse)
async def how_to_page(request: Request):
    """How-to page for building and testing plugins"""
    return templates.TemplateResponse("how-to.html", {"request": request})


@app.get("/api/plugins", response_model=PluginListResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_plugins(request: Request):
    """API endpoint to get all available plugins"""
    plugins = plugin_manager.get_all_plugins()
    return PluginListResponse(success=True, plugins=plugins)


@app.get("/plugin/{plugin_id}", response_class=HTMLResponse)
async def plugin_page(request: Request, plugin_id: str):
    """Plugin interaction page"""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return templates.TemplateResponse("plugin.html", {
        "request": request,
        "plugin": plugin
    })


@app.post("/api/plugin/{plugin_id}/execute")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def execute_plugin_api(
    plugin_id: str,
    request: Request,
    input_file: UploadFile = File(None),
    current_user: Optional[User] = Depends(optional_auth)
):
    """
    API endpoint to execute a plugin

    Requires authentication if ENABLE_AUTH=true
    Rate limited to prevent abuse
    File size limited to MAX_UPLOAD_SIZE_MB
    """
    try:
        logger.info(f"Executing plugin: {plugin_id}", extra={"user": getattr(current_user, 'username', 'anonymous')})
        form_data = await request.form()
        data = dict(form_data)
        
        if input_file:
            # Stream large files to temporary location instead of loading into memory
            temp_file_path = await _stream_upload_to_temp(input_file)
            data["input_file"] = {
                "filename": input_file.filename,
                "temp_path": temp_file_path,
                "size": os.path.getsize(temp_file_path)
            }

        plugin_input = PluginInput(plugin_id=plugin_id, data=data)
        result = plugin_manager.execute_plugin(plugin_input)

        if result.success and result.file_data:
            return FileResponse(
                path=result.file_data["file_path"],
                filename=result.file_data["file_name"],
                media_type="application/octet-stream"
            )
        elif not result.success:
             return JSONResponse(status_code=400, content=result.dict())

        return result

    except Exception as e:
        return PluginExecutionResponse(
            success=False,
            plugin_id=plugin_id,
            error=str(e)
        )


@app.post("/plugin/{plugin_id}/execute", response_class=HTMLResponse)
async def execute_plugin_web(request: Request, plugin_id: str, input_file: UploadFile = File(None)):
    """Web interface for plugin execution"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        if input_file:
            # Stream large files to temporary location instead of loading into memory
            temp_file_path = await _stream_upload_to_temp(input_file)
            data["input_file"] = {
                "filename": input_file.filename,
                "temp_path": temp_file_path,
                "size": os.path.getsize(temp_file_path)
            }

        plugin_input = PluginInput(plugin_id=plugin_id, data=data)
        result = plugin_manager.execute_plugin(plugin_input)

        if result.success and result.file_data:
            # Clean up old downloads before serving new file
            cleanup_downloads_directory(max_age_hours=1)  # Clean files older than 1 hour
            
            return FileResponse(
                path=result.file_data["file_path"],
                filename=result.file_data["file_name"],
                media_type="application/octet-stream"
            )

        plugin = plugin_manager.get_plugin(plugin_id)
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "plugin": plugin,
            "result": result,
            "input_data": data
        })
    except Exception as e:
        plugin = plugin_manager.get_plugin(plugin_id)
        error_result = PluginExecutionResponse(
            success=False,
            plugin_id=plugin_id,
            error=str(e)
        )
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "plugin": plugin,
            "result": error_result,
            "input_data": {}
        })


@app.get("/api/plugin/{plugin_id}")
async def get_plugin_info(plugin_id: str):
    """Get information about a specific plugin"""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"success": True, "plugin": plugin}


@app.post("/api/refresh-plugins")
async def refresh_plugins():
    """Refresh the plugin list"""
    plugin_manager.refresh_plugins()
    plugins = plugin_manager.get_all_plugins()
    return {"success": True, "message": "Plugins refreshed", "count": len(plugins)}


@app.post("/api/cleanup-downloads")
async def cleanup_downloads(max_age_hours: int = 24):
    """Clean up old files from downloads directory"""
    result = cleanup_downloads_directory(max_age_hours)
    return {"success": True, "cleanup_result": result}


@app.get("/api/plugin-compliance")
async def check_plugin_compliance():
    """
    Check plugin compliance with the rule: ALL PLUGINS MUST DEFINE PYDANTIC RESPONSE MODELS
    
    Returns information about which plugins are compliant and which need to be updated.
    """
    all_plugins = plugin_manager.get_all_plugins()
    non_compliant = plugin_manager.get_non_compliant_plugins()
    
    compliant_plugins = []
    for plugin in all_plugins:
        status = getattr(plugin, 'compliance_status', {})
        if status.get('compliant', False):
            compliant_plugins.append({
                "plugin_id": plugin.id,
                "plugin_name": plugin.name,
                "response_model": status.get('response_model', 'Unknown')
            })
    
    return {
        "success": True,
        "rule": "ALL PLUGINS MUST DEFINE PYDANTIC RESPONSE MODELS",
        "summary": {
            "total_plugins": len(all_plugins),
            "compliant_count": len(compliant_plugins),
            "non_compliant_count": len(non_compliant),
            "compliance_percentage": round((len(compliant_plugins) / len(all_plugins) * 100) if all_plugins else 0, 2)
        },
        "compliant_plugins": compliant_plugins,
        "non_compliant_plugins": non_compliant,
        "fix_instructions": {
            "steps": [
                "Make your plugin class inherit from BasePlugin",
                "Define a Pydantic response model inheriting from BasePluginResponse", 
                "Implement the get_response_model() class method",
                "Ensure execute() returns data that validates against your model"
            ],
            "example_code": """
from typing import Dict, Any, Type
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse

class YourPluginResponse(BasePluginResponse):
    result: str = Field(..., description="Your result field")
    count: int = Field(..., description="Some count")

class Plugin(BasePlugin):
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        return YourPluginResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": "some value",
            "count": 42
        }
            """
        }
    }


# ========== CHAIN MANAGEMENT ENDPOINTS ==========

@app.get("/chain-builder", response_class=HTMLResponse)
async def chain_builder(request: Request):
    """Visual chain builder interface"""
    return templates.TemplateResponse("chain_builder.html", {
        "request": request
    })

@app.get("/chains", response_class=HTMLResponse)
async def chains_list(request: Request):
    """List all chains interface"""
    chains = chain_manager.list_chains()
    return templates.TemplateResponse("chains.html", {
        "request": request,
        "chains": chains
    })

@app.post("/api/chains")
async def create_chain(chain_data: Dict[str, Any]):
    """Create a new plugin chain"""
    try:
        if "definition" in chain_data:
            # Save a complete chain definition
            chain = ChainDefinition(**chain_data["definition"])
            success = chain_manager.save_chain(chain)
            if success:
                return {"success": True, "chain_id": chain.id}
            else:
                raise HTTPException(status_code=500, detail="Failed to save chain")
        else:
            # Create a new empty chain
            chain = chain_manager.create_chain(
                name=chain_data.get("name", "Untitled Chain"),
                description=chain_data.get("description", ""),
                author=chain_data.get("author")
            )
            return {"success": True, "chain": chain.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/chains")
async def list_chains(tags: str = None, template_only: bool = False):
    """List all available chains"""
    tag_list = tags.split(",") if tags else None
    chains = chain_manager.list_chains(tags=tag_list, template_only=template_only)
    return {
        "success": True, 
        "chains": [chain.dict() for chain in chains]
    }

@app.get("/api/chains/search")
async def search_chains(q: str = "", tags: str = None):
    """Search chains by query and tags"""
    tag_list = tags.split(",") if tags else None
    results = chain_manager.search_chains(query=q, tags=tag_list)
    return {"success": True, "results": results}

@app.get("/api/chains/{chain_id}")
async def get_chain(chain_id: str):
    """Get a specific chain definition"""
    chain = chain_manager.load_chain(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    return {"success": True, "chain": chain.dict()}

@app.put("/api/chains/{chain_id}")
async def update_chain(chain_id: str, chain_data: Dict[str, Any]):
    """Update a chain definition"""
    try:
        chain = ChainDefinition(**chain_data)
        chain.id = chain_id  # Ensure ID matches URL
        success = chain_manager.save_chain(chain)
        if success:
            return {"success": True, "chain": chain.dict()}
        else:
            raise HTTPException(status_code=500, detail="Failed to update chain")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/chains/{chain_id}")
async def delete_chain(chain_id: str):
    """Delete a chain"""
    success = chain_manager.delete_chain(chain_id)
    if success:
        return {"success": True, "message": "Chain deleted"}
    else:
        raise HTTPException(status_code=404, detail="Chain not found")

@app.post("/api/chains/{chain_id}/duplicate")
async def duplicate_chain(chain_id: str, data: Dict[str, Any]):
    """Duplicate an existing chain"""
    new_name = data.get("name")
    duplicate = chain_manager.duplicate_chain(chain_id, new_name)
    if duplicate:
        return {"success": True, "chain": duplicate.dict()}
    else:
        raise HTTPException(status_code=404, detail="Chain not found")

@app.post("/api/chains/validate")
async def validate_chain(chain_data: Dict[str, Any]):
    """Validate a chain definition"""
    try:
        chain = ChainDefinition(**chain_data)
        validation = chain_manager.validate_chain(chain)
        return {"success": True, "validation": validation.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/chains/{chain_id}/execute")
async def execute_chain(chain_id: str, input_data: Dict[str, Any]):
    """Execute a plugin chain"""
    try:
        result = await chain_manager.execute_chain(chain_id, input_data)
        return result.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chains/{chain_id}/history")
async def get_execution_history(chain_id: str, limit: int = 50):
    """Get execution history for a chain"""
    history = chain_manager.get_execution_history(chain_id, limit)
    return {
        "success": True, 
        "history": [result.dict() for result in history]
    }

@app.get("/api/chains/{chain_id}/analytics")
async def get_chain_analytics(chain_id: str):
    """Get analytics for a specific chain"""
    analytics = chain_manager.get_chain_analytics(chain_id)
    if analytics:
        return {"success": True, "analytics": analytics.dict()}
    else:
        return {"success": True, "analytics": None}

@app.get("/api/system/analytics")
async def get_system_analytics():
    """Get system-wide analytics"""
    analytics = chain_manager.get_system_analytics()
    return {"success": True, "analytics": analytics}

@app.get("/api/plugins/{plugin_id}/schema")
async def get_plugin_schema(plugin_id: str):
    """Get plugin input/output schema for chain building"""
    schema = chain_manager.get_plugin_schema(plugin_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"success": True, "schema": schema}

@app.get("/api/chains/{chain_id}/connections/{source_node_id}")
async def get_compatible_connections(chain_id: str, source_node_id: str):
    """Get possible connections from a source node"""
    chain = chain_manager.load_chain(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    compatible = chain_manager.get_compatible_connections(chain, source_node_id)
    return {"success": True, "compatible_connections": compatible}

# ========== TEMPLATE MANAGEMENT ==========

@app.get("/api/templates")
async def list_templates(category: str = None):
    """List all available templates"""
    templates = chain_manager.list_templates(category=category)
    return {
        "success": True, 
        "templates": [template.dict() for template in templates]
    }

@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template"""
    template = chain_manager.load_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, "template": template.dict()}

@app.post("/api/templates/{template_id}/create-chain")
async def create_chain_from_template(template_id: str, data: Dict[str, Any]):
    """Create a new chain from a template"""
    chain = chain_manager.create_chain_from_template(
        template_id, 
        data.get("name", "Untitled Chain"),
        data.get("author")
    )
    if chain:
        return {"success": True, "chain": chain.dict()}
    else:
        raise HTTPException(status_code=404, detail="Template not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 