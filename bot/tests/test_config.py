from bot import config


def test_config_prefers_first_webapp_candidate(monkeypatch):
    monkeypatch.setenv(
        'WEBAPP_URL',
        'https://mini.example.com/app/, https://backup.example.com/secondary',
    )
    cfg = config.Config.load()
    assert cfg.webapp_url == 'https://mini.example.com/app/'
    assert cfg.webapp_webview_url == 'https://mini.example.com/app/'


def test_config_webapp_url_defaults_when_missing(monkeypatch):
    monkeypatch.delenv('WEBAPP_URL', raising=False)
    cfg = config.Config.load()
    assert cfg.webapp_url == config._DEF_WEBAPP
    assert cfg.webapp_webview_url is None or cfg.webapp_webview_url == config._DEF_WEBAPP
