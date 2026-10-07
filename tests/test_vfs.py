"""Тесты модуля загрузки VFS."""
import json
import tempfile
import unittest
from src.emulator import load_vfs
class TestVFS(unittest.TestCase):
    """Набор тестов для проверки загрузки файловой системы."""
    def test_valid_json(self):
        """Проверяет корректную загрузку валидного JSON."""
        data = {"/": {"type": "dir", "content": ["test"]}}
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            result = load_vfs(f.name)
        self.assertIn("/", result)
        self.assertEqual(result["/"]["content"], ["test"])
    def test_missing_file(self):
        """Проверяет возврат дефолтной ФС при отсутствии файла."""
        result = load_vfs("/nonexistent/path.json")
        self.assertIn("/", result)
    def test_invalid_json(self):
        """Проверяет обработку невалидного JSON."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write("{invalid json}")
            f.flush()
            result = load_vfs(f.name)
        self.assertIn("/", result)
