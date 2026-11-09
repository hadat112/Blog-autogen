from app.integrations.publishers.facebook_page import FacebookPagePublisher


def test_photo_file_uses_multipart_and_closes_handle(tmp_path, monkeypatch):
    import app.integrations.publishers.facebook_page as module
    image = tmp_path / 'photo.jpg'
    image.write_bytes(b'\xff\xd8\xffimage')
    captured = {}
    class Response:
        status_code = 200
        def json(self): return {'post_id': 'post-1'}
    def post(url, **kwargs):
        captured.update(kwargs)
        assert kwargs['files']['source'].read() == image.read_bytes()
        assert 'url' not in kwargs['data']
        assert kwargs['data']['caption'] == 'Caption'
        return Response()
    monkeypatch.setattr(module.requests, 'post', post)
    assert FacebookPagePublisher('page', 'token').publish_photo_file('Caption', str(image)) == 'post-1'
    assert captured['files']['source'].closed
