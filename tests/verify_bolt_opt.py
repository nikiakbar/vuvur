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
    @patch('os.path.exists')
    @patch('os.path.abspath')
    @patch('app.thumbnails.send_file')
    def test_thumb_fast_path(self, mock_send_file, mock_abspath, mock_exists, mock_get_media_row):
        # THUMB_DIR is /app/data/thumbs
        # abs_dst.startswith(os.path.abspath(THUMB_DIR))

        def exists_side_effect(p):
             if '1.jpg' in p:
                 return True
             return False

        mock_exists.side_effect = exists_side_effect
        # Make sure abspath for THUMB_DIR and the file match prefix
        mock_abspath.side_effect = lambda p: p

        mock_send_file.return_value = 'mocked_file'

        with patch('app.api_key_middleware.API_SECRET', None):
            with patch('app.thumbnails.THUMB_DIR', '/app/data/thumbs'):
                with patch('os.path.commonpath', return_value='/app/data/thumbs'):
                    response = self.client.get('/api/thumbnails/1')

        self.assertEqual(response.status_code, 200)
        mock_get_media_row.assert_not_called()

    @patch('app.thumbnails.get_media_row')
    @patch('os.path.exists')
    @patch('os.path.abspath')
    @patch('app.thumbnails.send_file')
    @patch('app.thumbnails.GENERATION_SEMAPHORE')
    def test_thumb_slow_path(self, mock_semaphore, mock_send_file, mock_abspath, mock_exists, mock_get_media_row):
        mock_exists.side_effect = [
            False, # fast path .jpg
            False, # fast path .gif
            True,  # src exists check
            True   # final exist check
        ]
        mock_abspath.side_effect = lambda p: p

        mock_get_media_row.return_value = {'path': '/mnt/gallery/image.jpg', 'type': 'image'}
        mock_send_file.return_value = 'mocked_file'
        mock_semaphore.acquire.return_value = True

        with patch('app.api_key_middleware.API_SECRET', None):
            with patch('app.thumbnails.THUMB_DIR', '/app/data/thumbs'):
                with patch('os.path.commonpath', return_value='/app/data/thumbs'):
                    with patch('app.thumbnails.create_image_version') as mock_create:
                        response = self.client.get('/api/thumbnails/2')

        mock_get_media_row.assert_called_once_with(2)
        mock_create.assert_called_once()
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
