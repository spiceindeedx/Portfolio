import unittest
from unittest.mock import patch, MagicMock
from app import app, get_recent_logs, get_all_files, get_file_info, connect_db

class FlaskAppTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('app.get_recent_logs')
    def test_home(self, mock_get_recent_logs):
        mock_get_recent_logs.return_value = [
            ('2023-06-01 12:00:00', 'ERROR', 'An error occurred', '/path/to/file', 'filename.txt')
        ]
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'An error occurred', response.data)

    @patch('app.get_all_files')
    def test_filepage(self, mock_get_all_files):
        mock_get_all_files.return_value = [
            (1, '/path/to/file', 'filename.txt')
        ]
        response = self.client.get('/filepage')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'filename.txt', response.data)

    @patch('app.get_file_info')
    def test_file_info(self, mock_get_file_info):
        mock_get_file_info.return_value = (
            (1, '/path/to/file', 'filename.txt', '2023-06-01 12:00:00', 'abc123'),
            [('2023-06-01 12:00:00', 'ERROR', 'An error occurred', 1)],
            {1: ['Note 1']}
        )
        response = self.client.get('/file/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'filename.txt', response.data)
        self.assertIn(b'An error occurred', response.data)
        self.assertIn(b'Note 1', response.data)

    @patch('app.connect_db')
    def test_attach_note(self, mock_connect_db):
        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value
        mock_connect_db.return_value = mock_conn
        
        response = self.client.post('/attach_note/1/1', data={'note_text': 'Test note'}, follow_redirects=True)

        print(f"Actual calls: {mock_cursor.execute.mock_calls}")

        expected_call = (("INSERT INTO Notes (note_text, entry_id) VALUES (?, ?)", ('Test note', '1')),)
        
        self.assertIn(expected_call[0], [call[1] for call in mock_cursor.execute.mock_calls])
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
