import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add api directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from flask import Flask

class TestThumbnailOptimization(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        # Mocking the blueprint and required decorators
        from app.thumbnails import bp
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()

    @patch('app.thumbnails.get_media_row')
    @patch('os.path.isfile')
    @patch('app.thumbnails.send_from_directory')
    def test_thumb_fast_path(self, mock_send_from_dir, mock_isfile, mock_get_media_row):
        # Setup mocks
        def isfile_side_effect(p):
             if '1.jpg' in p:
                 return True
             return False

        mock_isfile.side_effect = isfile_side_effect
        mock_send_from_dir.return_value = 'mocked_file'

        with patch('app.api_key_middleware.API_SECRET', None):
            response = self.client.get('/api/thumbnails/1')

        self.assertEqual(response.status_code, 200)
        mock_get_media_row.assert_not_called()
        mock_send_from_dir.assert_called_once()

    @patch('app.thumbnails.get_media_row')
    @patch('os.path.isfile')
    @patch('os.path.exists')
    @patch('app.thumbnails.send_file')
    @patch('app.thumbnails.send_from_directory')
    @patch('app.thumbnails.GENERATION_SEMAPHORE')
    def test_thumb_slow_path(self, mock_semaphore, mock_send_from_dir, mock_send_file, mock_exists, mock_isfile, mock_get_media_row):
        mock_isfile.return_value = False
        mock_exists.side_effect = [
            True,  # src exists check
            True   # final exist check
        ]

        mock_get_media_row.return_value = {'path': '/mnt/gallery/image.jpg', 'type': 'image'}
        mock_send_file.return_value = 'mocked_file'
        mock_semaphore.acquire.return_value = True

        with patch('app.api_key_middleware.API_SECRET', None):
            with patch('app.thumbnails.create_image_version') as mock_create:
                response = self.client.get('/api/thumbnails/2')

        mock_get_media_row.assert_called_once_with(2)
        mock_create.assert_called_once()
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
