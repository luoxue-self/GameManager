import install


def test_mirror_table_complete():
    assert set(install.ORDER) <= set(install.MIRRORS)
    assert install.MIRRORS["pypi"][1].startswith("https://")
    for name, url in install.MIRRORS.values():
        assert name
        assert url.startswith(("http://", "https://"))


def test_choose_mirror_prefers_first_reachable():
    name, url = install.choose_mirror("auto", probe_func=lambda u: True)
    assert name == "阿里云"
    assert url == install.MIRRORS["aliyun"][1]


def test_choose_mirror_falls_back_in_order():
    seen = []

    def fake(url):
        seen.append(url)
        return "ustc" in url

    name, url = install.choose_mirror("auto", probe_func=fake)
    assert name == "中科大"
    assert url == install.MIRRORS["ustc"][1]
    assert seen[:2] == [install.MIRRORS["aliyun"][1],
                        install.MIRRORS["tsinghua"][1]]


def test_choose_mirror_named():
    name, url = install.choose_mirror("tsinghua", probe_func=lambda u: False)
    assert name == "清华 TUNA"
    assert url == install.MIRRORS["tsinghua"][1]


def test_choose_mirror_custom_index():
    name, url = install.choose_mirror(
        "auto", index_url="https://mirror.example.com/pypi/simple/",
        probe_func=lambda u: False)
    assert name == "自定义镜像"
    assert url == "https://mirror.example.com/pypi/simple"


def test_pip_command_contains_mirror_and_requirements():
    cmd = install.pip_command("python", "requirements.txt",
                              "https://mirror.example.com/simple")
    assert cmd[:3] == ["python", "-m", "pip"]
    assert "-r" in cmd and "requirements.txt" in cmd
    assert "-i" in cmd and "https://mirror.example.com/simple" in cmd
    assert "--prefer-binary" in cmd


def test_pip_command_trusted_host():
    cmd = install.pip_command("python", "r.txt", "http://m/simple",
                              trusted_host="m")
    assert cmd[-2:] == ["--trusted-host", "m"]
