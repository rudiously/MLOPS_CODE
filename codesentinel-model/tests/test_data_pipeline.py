import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))

from schema import CodeSample, validate_sample  # noqa: E402
from dedup_split import dedup, repo_level_split  # noqa: E402
from augment import rename_variables, insert_dead_code, reorder_independent_statements  # noqa: E402


def make_sample(id_, repo, code, label=1, cwe_id=None, severity=None):
    return CodeSample(id=id_, source_dataset="test", language="c", repo=repo,
                       code=code, label=label, cwe_id=cwe_id, severity=severity)


def test_validate_sample_rejects_empty_code():
    s = make_sample("1", "repoA", "")
    errors = validate_sample(s)
    assert "empty code body" in errors


def test_validate_sample_rejects_bad_label():
    s = make_sample("1", "repoA", "int main(){}", label=5)
    errors = validate_sample(s)
    assert any("label must be" in e for e in errors)


def test_dedup_removes_exact_and_whitespace_duplicates():
    a = make_sample("1", "repoA", "int main() { return 0; }")
    b = make_sample("2", "repoB", "int main()  {  return 0;  }")  # same modulo whitespace
    c = make_sample("3", "repoC", "int other() { return 1; }")
    deduped, removed = dedup([a, b, c])
    assert removed == 1
    assert len(deduped) == 2


def test_dedup_prefers_richer_metadata():
    a = make_sample("1", "repoA", "int main() { return 0; }", cwe_id=None)
    b = make_sample("2", "repoB", "int main() { return 0; }", cwe_id="CWE-119")
    deduped, _ = dedup([a, b])
    assert len(deduped) == 1
    assert deduped[0].cwe_id == "CWE-119"


def test_repo_level_split_never_splits_a_repo_across_sets():
    samples = [make_sample(str(i), f"repo{i % 5}", "code") for i in range(50)]
    train, val, test = repo_level_split(samples, test_frac=0.2, val_frac=0.2, seed=1)

    train_repos = {s.repo for s in train}
    val_repos = {s.repo for s in val}
    test_repos = {s.repo for s in test}

    assert train_repos.isdisjoint(val_repos)
    assert train_repos.isdisjoint(test_repos)
    assert val_repos.isdisjoint(test_repos)
    assert len(train) + len(val) + len(test) == len(samples)


def test_augment_rename_variables_preserves_structure():
    code = "int total = 0;\nfor (int i = 0; i < n; i++) { total += i; }"
    renamed = rename_variables(code, rename_frac=1.0, seed=0)
    assert renamed.count("{") == code.count("{")
    assert renamed.count(";") == code.count(";")


def test_augment_insert_dead_code_adds_a_line():
    code = "int a = 1;\nint b = 2;\nreturn a + b;"
    augmented = insert_dead_code(code, seed=0)
    assert len(augmented.split("\n")) == len(code.split("\n")) + 1


def test_augment_reorder_is_idempotent_on_single_line():
    code = "int a = 1;"
    assert reorder_independent_statements(code, seed=0) == code
