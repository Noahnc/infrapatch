from infrapatch.action.__main__ import get_credentials_from_string


def test_get_credentials_from_string():
    # Test case 1: Empty credentials string
    credentials_string = ""
    expected_result = {}
    assert get_credentials_from_string(credentials_string) == expected_result

    # Test case 2: Single line credentials string
    credentials_string = "username=abc123"
    expected_result = {"username": "abc123"}
    assert get_credentials_from_string(credentials_string) == expected_result

    # Test case 3: Multiple line credentials string
    credentials_string = "username=abc123\npassword=xyz789\ntoken=123456"
    expected_result = {"username": "abc123", "password": "xyz789", "token": "123456"}
    assert get_credentials_from_string(credentials_string) == expected_result

    # Test case 4: Invalid credentials string
    credentials_string = "username=abc123\npassword"
    try:
        get_credentials_from_string(credentials_string)
    except Exception as e:
        assert str(e) == "Error processing secrets: 'not enough values to unpack (expected 2, got 1)'"
