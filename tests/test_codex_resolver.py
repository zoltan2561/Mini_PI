import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.codex_bridge import resolve_codex


class CodexResolverTest(unittest.TestCase):
    def test_path_cli_does_not_query_store(self):
        with patch('tools.codex_bridge.shutil.which',return_value='C:/cli/codex.exe'), patch('tools.codex_bridge.subprocess.run') as run:
            self.assertEqual(resolve_codex(),'C:/cli/codex.exe')
            run.assert_not_called()

    @unittest.skipUnless(os.name=='nt','Windows resolver')
    def test_store_resource_cli_is_selected_instead_of_desktop_gui(self):
        target=Path('C:/Program Files/WindowsApps/OpenAI.Codex_test/app/resources/codex.exe')
        result=SimpleNamespace(returncode=0,stdout=str(target))
        with patch('tools.codex_bridge.shutil.which',return_value=None), patch('tools.codex_bridge.Path.is_file',lambda p:p==target), patch('tools.codex_bridge.subprocess.run',return_value=result):
            self.assertEqual(resolve_codex(),str(target))
            self.assertNotEqual(Path(resolve_codex()).parent.name,'app')

    @unittest.skipUnless(os.name=='nt','Windows resolver')
    def test_npm_native_binary_is_used_without_cmd_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root/'Roaming/npm/node_modules/@openai/codex/vendor/x86_64-pc-windows-msvc/codex/codex.exe'
            target.parent.mkdir(parents=True)
            target.touch()
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root/'Local'),'APPDATA':str(root/'Roaming')}), patch('tools.codex_bridge.shutil.which',return_value=None), patch('tools.codex_bridge.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='')):
                self.assertEqual(resolve_codex(),str(target))
