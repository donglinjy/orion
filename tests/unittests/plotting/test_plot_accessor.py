"""Collection of tests for :mod:`orion.plotting.orion.plotting.PlotAccessor`."""
import pytest

from orion.plotting.base import PlotAccessor
from orion.testing import create_experiment

config = dict(
    name="experiment-name",
    space={"x": "uniform(0, 200)"},
    metadata={
        "user": "test-user",
        "orion_version": "XYZ",
        "VCS": {
            "type": "git",
            "is_dirty": False,
            "HEAD_sha": "test",
            "active_branch": None,
            "diff_sha": "diff",
        },
    },
    version=1,
    pool_size=1,
    max_trials=10,
    working_dir="",
    algorithms={"random": {"seed": 1}},
    producer={"strategy": "NoParallelStrategy"},
)


trial_config = {
    "experiment": 0,
    "status": "new",  # new, reserved, suspended, completed, broken
    "worker": None,
    "start_time": None,
    "end_time": None,
    "heartbeat": None,
    "results": [],
    "params": [],
}


def check_plot(plot, kind):
    """Verifies that existence of the plot"""
    assert plot
    assert kind.replace("_", " ") in plot.layout.title.text.lower()


def test_init_require_experiment():
    """Tests that a `PlotAccessor` requires an instance of `ExperimentClient`"""
    with pytest.raises(ValueError) as exception:
        PlotAccessor(None)

    assert "Parameter 'experiment' is None" in str(exception.value)


def test_call_nonexistent_kind():
    """Tests that specifying a non existent kind will fail"""
    with create_experiment(config, trial_config, ["completed"]) as (_, _, experiment):
        pa = PlotAccessor(experiment)
        with pytest.raises(ValueError) as exception:
            pa(kind="nonexistent")

        assert "Plot of kind 'nonexistent' is not one of" in str(exception.value)


def test_regret_is_default_plot():
    """Tests that the regret plot is the default plot"""
    with create_experiment(config, trial_config, ["completed"]) as (_, _, experiment):
        pa = PlotAccessor(experiment)
        plot = pa()

        check_plot(plot, "regret")


@pytest.mark.parametrize("kind", ("lpi", "regret", "parallel_coordinates"))
def test_kind(kind):
    """Tests that a plot can be created from specifying `kind` as a parameter."""
    with create_experiment(config, trial_config, ["completed"]) as (_, _, experiment):
        pa = PlotAccessor(experiment)
        plot = pa(kind=kind)

        check_plot(plot, kind)


@pytest.mark.parametrize("kind", ("lpi", "regret", "parallel_coordinates"))
def test_call_to(kind):
    """Tests instance calls to `PlotAccessor.{kind}()`"""
    with create_experiment(config, trial_config, ["completed"]) as (_, _, experiment):
        pa = PlotAccessor(experiment)
        plot = getattr(pa, kind)()

        check_plot(plot, kind)
