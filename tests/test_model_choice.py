"""Every model the desk uses is served by Featherless."""
from saadhak.practitioner.llm import model_chain, providers


def test_every_provider_is_featherless():
    for _, url, _ in providers():
        assert "featherless.ai" in url


def test_more_than_one_model_so_a_throttle_does_not_stop_the_desk():
    assert len(model_chain()) >= 2


def test_the_chain_has_no_duplicates():
    chain = model_chain()
    assert len(chain) == len(set(chain))
