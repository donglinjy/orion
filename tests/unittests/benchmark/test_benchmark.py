#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for :mod:`orion.benchmark.Benchmark`."""

import datetime

import plotly
import pytest

import orion.core.io.experiment_builder as experiment_builder
from orion.benchmark import Benchmark, Study
from orion.benchmark.assessment import AverageRank, AverageResult
from orion.benchmark.task import CarromTable, RosenBrock
from orion.client.experiment import ExperimentClient
from orion.core.worker.experiment import Experiment
from orion.testing import OrionState, generate_trials

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
    "status": "completed",
    "worker": None,
    "start_time": None,
    "end_time": None,
    "heartbeat": None,
    "results": [],
    "params": [],
}


@pytest.fixture
def algorithms():
    """Return a list of algorithms suitable for Orion experiment"""
    return [{"random": {"seed": 1}}, {"tpe": {"seed": 1}}]


@pytest.fixture
def generate_experiment_trials(algorithms, task_num=2, max_trial=3):
    """Return a list of experiments and trials"""
    gen_exps = []
    gen_trials = []
    algo_num = len(algorithms)
    for i in range(task_num * algo_num):
        import copy

        exp = copy.deepcopy(config)
        exp["_id"] = i
        exp["name"] = "experiment-name-{}".format(i)
        exp["algorithms"] = algorithms[i % algo_num]
        exp["max_trials"] = max_trial
        exp["metadata"]["datetime"] = datetime.datetime.utcnow()
        gen_exps.append(exp)
        for j in range(max_trial):
            trial = copy.deepcopy(trial_config)
            trial["_id"] = "{}{}".format(i, j)
            trial["experiment"] = i
            trials = generate_trials(trial, ["completed"])
            gen_trials.extend(trials)

    return task_num, gen_exps, gen_trials


@pytest.fixture
def benchmark(algorithms):
    """Return a benchmark instance"""
    return Benchmark(
        name="benchmark007",
        algorithms=algorithms,
        targets=[
            {
                "assess": [AverageResult(2), AverageRank(2)],
                "task": [RosenBrock(25, dim=3), CarromTable(20)],
            }
        ],
    )


@pytest.fixture
def study(benchmark, algorithms):
    """Return a study instance"""
    return Study(benchmark, algorithms, AverageResult(2), RosenBrock(25, dim=3))


class TestBenchmark:
    """Test Benchmark"""

    def test_creation(self, benchmark):
        """Test benchmark instance creation"""
        cfg = {
            "name": "benchmark007",
            "algorithms": [{"random": {"seed": 1}}, {"tpe": {"seed": 1}}],
            "targets": [
                {
                    "assess": [
                        {
                            "orion-benchmark-assessment-averageresult-AverageResult": {
                                "task_num": 2
                            }
                        },
                        {
                            "orion-benchmark-assessment-averagerank-AverageRank": {
                                "task_num": 2
                            }
                        },
                    ],
                    "task": [
                        {
                            "orion-benchmark-task-rosenbrock-RosenBrock": {
                                "dim": 3,
                                "max_trials": 25,
                            }
                        },
                        {
                            "orion-benchmark-task-carromtable-CarromTable": {
                                "max_trials": 20
                            }
                        },
                    ],
                }
            ],
        }
        assert benchmark.configuration == cfg

    def test_setup_studies(self, benchmark):
        """Test to setup studies for benchmark"""
        with OrionState():
            benchmark.setup_studies()

            assert (
                str(benchmark.studies)
                == "[Study(assessment=AverageResult, task=RosenBrock, algorithms=[random,tpe]), "
                "Study(assessment=AverageResult, task=CarromTable, algorithms=[random,tpe]), "
                "Study(assessment=AverageRank, task=RosenBrock, algorithms=[random,tpe]), "
                "Study(assessment=AverageRank, task=CarromTable, algorithms=[random,tpe])]"
            )

        assert len(benchmark.studies) == 4

    def test_process(self, benchmark, study):
        """Test to process a benchmark"""
        with OrionState():
            study.setup_experiments()
            benchmark.studies = [study]
            benchmark.process()
            name = "benchmark007_AverageResult_RosenBrock_0_0"
            experiment = experiment_builder.build(name)

            assert experiment is not None

    def test_status(self, benchmark, study, algorithms, generate_experiment_trials):
        """Test to get the status of a benchmark"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            benchmark.studies = [study]

            assert benchmark.status(silent=True) == [
                {
                    "Algorithms": "random",
                    "Assessments": "AverageResult",
                    "Tasks": "RosenBrock",
                    "Total Experiments": 2,
                    "Completed Experiments": 2,
                    "Submitted Trials": 6,
                },
                {
                    "Algorithms": "tpe",
                    "Assessments": "AverageResult",
                    "Tasks": "RosenBrock",
                    "Total Experiments": 2,
                    "Completed Experiments": 2,
                    "Submitted Trials": 6,
                },
            ]

    def test_analysis(self, benchmark, study, algorithms, generate_experiment_trials):
        """Test to analysis benchmark result"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            benchmark.studies = [study]

            figures = benchmark.analysis()

            assert len(figures) == 1
            assert type(figures[0]) is plotly.graph_objects.Figure

    def test_experiments(
        self, benchmark, study, algorithms, generate_experiment_trials
    ):
        """Test to get experiments list of a benchmark"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            benchmark.studies = [study]

            assert benchmark.experiments(silent=True) == [
                {
                    "Algorithm": "random",
                    "Experiment Name": "experiment-name-0",
                    "Number Trial": 3,
                    "Best Evaluation": 0,
                },
                {
                    "Algorithm": "tpe",
                    "Experiment Name": "experiment-name-1",
                    "Number Trial": 3,
                    "Best Evaluation": 0,
                },
                {
                    "Algorithm": "random",
                    "Experiment Name": "experiment-name-2",
                    "Number Trial": 3,
                    "Best Evaluation": 0,
                },
                {
                    "Algorithm": "tpe",
                    "Experiment Name": "experiment-name-3",
                    "Number Trial": 3,
                    "Best Evaluation": 0,
                },
            ]


class TestStudy:
    """Test Study"""

    def test_creation(self, study):
        """Test study instance creation"""
        assert (
            str(study) == "Study(assessment=AverageResult, "
            "task=RosenBrock, algorithms=[random,tpe])"
        )

    def test_setup_experiments(self, study):
        """Test to setup experiments for study"""
        with OrionState():
            study.setup_experiments()

            assert len(study.experiments_info) == 4
            assert isinstance(study.experiments_info[0][1], ExperimentClient)

    def test_execute(self, study):
        """Test to execute a study"""
        with OrionState():
            study.setup_experiments()
            study.execute()
            name = "benchmark007_AverageResult_RosenBrock_0_0"
            experiment = experiment_builder.build(name)

            assert experiment is not None

    def test_status(self, study, algorithms, generate_experiment_trials):
        """Test to get status of a study"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            assert study.status() == [
                {
                    "algorithm": "random",
                    "assessment": "AverageResult",
                    "task": "RosenBrock",
                    "experiments": 2,
                    "completed": 2,
                    "trials": 6,
                },
                {
                    "algorithm": "tpe",
                    "assessment": "AverageResult",
                    "task": "RosenBrock",
                    "experiments": 2,
                    "completed": 2,
                    "trials": 6,
                },
            ]

    def test_display(self, study, algorithms, generate_experiment_trials):
        """Test to get the ploty figure of a study"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            plot = study.display()

            assert type(plot) is plotly.graph_objects.Figure

    def test_experiments(self, study, algorithms, generate_experiment_trials):
        """Test to get experiments of a study"""
        algo_num = len(algorithms)
        task_num, gen_exps, gen_trials = generate_experiment_trials

        with OrionState(experiments=gen_exps, trials=gen_trials):
            experiments = []
            experiments_info = []
            for i in range(2 * algo_num):
                experiment = experiment_builder.build("experiment-name-{}".format(i))
                experiments.append(experiment)

            for index, exp in enumerate(experiments):
                experiments_info.append((int(index / task_num), exp))

            study.experiments_info = experiments_info

            experiments = study.experiments()

            assert len(experiments) == 2 * algo_num
            assert isinstance(experiments[0], Experiment)