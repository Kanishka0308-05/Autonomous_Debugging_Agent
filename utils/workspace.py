import os
import shutil
import tempfile
import zipfile
from typing import Tuple, Optional, List

class WorkspaceManager:
    """
    Manages temporary workspaces for ZIP extractions safely.
    Prevents path traversal vulnerabilities and resolves project root directories.
    """
    
    @staticmethod
    def extract_zip(zip_path_or_bytes) -> Tuple[str, str, Optional[str]]:
        """
        Safely extracts a ZIP file or file-like object into a unique temporary directory.
        Returns: (temp_dir_path, project_root_path, error_message)
        """
        temp_dir = tempfile.mkdtemp(prefix="debug_workspace_")
        
        try:
            if isinstance(zip_path_or_bytes, (str, bytes, os.PathLike)):
                with zipfile.ZipFile(zip_path_or_bytes, 'r') as zf:
                    WorkspaceManager._safe_extract(zf, temp_dir)
            else:
                with zipfile.ZipFile(zip_path_or_bytes, 'r') as zf:
                    WorkspaceManager._safe_extract(zf, temp_dir)
                    
            project_root = WorkspaceManager.resolve_project_root(temp_dir)
            return temp_dir, project_root, None
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return "", "", "Invalid ZIP file format. Please upload a valid .zip archive."
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return "", "", f"Failed to extract ZIP file: {str(e)}"

    @staticmethod
    def _safe_extract(zip_file: zipfile.ZipFile, target_dir: str):
        """Extract zip members while preventing Zip Slip (path traversal) attacks."""
        target_dir_abs = os.path.abspath(target_dir)
        for member in zip_file.infolist():
            # Resolve target path
            extracted_path = os.path.abspath(os.path.join(target_dir, member.filename))
            if not extracted_path.startswith(target_dir_abs + os.sep) and extracted_path != target_dir_abs:
                raise Exception(f"Security error: Zip member path '{member.filename}' attempts path traversal outside target directory.")
            zip_file.extract(member, target_dir)

    @staticmethod
    def resolve_project_root(extracted_dir: str) -> str:
        """
        If the ZIP contains a single top-level directory (e.g. 'my_project/...'),
        resolve that directory as the project root.
        """
        items = [i for i in os.listdir(extracted_dir) if not i.startswith('.') and not i.startswith('__MACOSX')]
        if len(items) == 1:
            single_path = os.path.join(extracted_dir, items[0])
            if os.path.isdir(single_path):
                return single_path
        return extracted_dir

    @staticmethod
    def cleanup(temp_dir: str):
        """Safely removes the temporary workspace directory."""
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
