import pytest
from blood_donation_screening import process_donor_cohort, verify_storage_centrifuge

# Example test case:
def test_single_accepted_donor():
    cohorts = [
        {
            "clinic_registered": True,
            "type": "standard",
            "fast_track": False,
            "donors": [{"age": 25, "weight_kg": 65, "hb": 14.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result["collected_ml"] == 450
    assert result["status"] == "ACCEPTED"

# --- Line coverage tests ---

def test_invalid_cohorts_type_raises():
    with pytest.raises(ValueError):
        process_donor_cohort("not-a-list", 450)

def test_invalid_volume_raises():
    with pytest.raises(ValueError):
        process_donor_cohort([], 0)

def test_unregistered_cohort_is_skipped():
    cohorts = [
        {
            "clinic_registered": False,
            "donors": [{"age": 25, "weight_kg": 65, "hb": 14.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_young_donor_is_deferred():
    cohorts = [
        {
            "clinic_registered": True,
            "donors": [{"age": 16, "weight_kg": 60, "hb": 14.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_underweight_donor_is_deferred():
    cohorts = [
        {
            "clinic_registered": True,
            "donors": [{"age": 30, "weight_kg": 45, "hb": 14.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_low_hemoglobin_standard_cohort_defers():
    cohorts = [
        {
            "clinic_registered": True,
            "type": "standard",
            "donors": [{"age": 25, "weight_kg": 65, "hb": 12.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_high_hemoglobin_is_deferred():
    cohorts = [
        {
            "clinic_registered": True,
            "donors": [{"age": 25, "weight_kg": 65, "hb": 18.5}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_fast_track_adds_bonus_volume():
    cohorts = [
        {
            "clinic_registered": True,
            "fast_track": True,
            "donors": [{"age": 25, "weight_kg": 65, "hb": 14.0}]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 500, "status": "ACCEPTED"}

def test_more_than_four_deferrals_flags_high_deferral():
    donors = [{"age": 16, "weight_kg": 60, "hb": 14.0} for _ in range(5)]
    cohorts = [{"clinic_registered": True, "donors": donors}]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "HIGH_DEFERRAL"}

def test_empty_donor_list_yields_zero():
    cohorts = [{"clinic_registered": True, "donors": []}]
    result = process_donor_cohort(cohorts, 450)
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_centrifuge_no_data():
    assert verify_storage_centrifuge([]) == "NO_DATA"

def test_centrifuge_stable_run():
    assert verify_storage_centrifuge([[3500, 3200, 3400]]) == "STABLE"

def test_centrifuge_single_drop_recovers():
    assert verify_storage_centrifuge([[2800, 3500, 3100]]) == "STABLE"

# --- Branch coverage tests ---

def test_low_hemoglobin_high_altitude_aborts_cohort():
    cohorts = [
        {
            "clinic_registered": True,
            "type": "high_altitude",
            "donors": [
                {"age": 25, "weight_kg": 65, "hb": 14.0},
                {"age": 30, "weight_kg": 70, "hb": 12.0},
                {"age": 40, "weight_kg": 75, "hb": 14.5}
            ]
        }
    ]
    result = process_donor_cohort(cohorts, 450)
    # First donor accepted (450 ml), low-hb donor zeroes the cohort and breaks
    # the loop, so the third donor is never processed.
    assert result == {"collected_ml": 0, "status": "ZERO_YIELD"}

def test_centrifuge_two_consecutive_drops_aborts():
    assert verify_storage_centrifuge([[3500, 2800, 2900]]) == "ABORT_SPIN"

def test_centrifuge_abort_in_second_run():
    assert verify_storage_centrifuge([[3500, 3200], [3100, 2500, 2400]]) == "ABORT_SPIN"
