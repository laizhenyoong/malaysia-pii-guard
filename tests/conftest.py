import pytest

from malaysia_pii_guard import AnonymizerEngine, DeanonymizeEngine, generate_key


@pytest.fixture(scope="session")
def key():
    return generate_key()


@pytest.fixture(scope="session")
def anonymizer(key):
    return AnonymizerEngine(key)


@pytest.fixture(scope="session")
def deanonymizer(key):
    return DeanonymizeEngine(key)
