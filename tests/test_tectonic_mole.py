"""Контрактные тесты роли A для гусеничного крота "Тектоник"."""

import unittest

from tectonic_mole import (
    CrazyVehicleError,
    MoleCannotSwim,
    MoleNoEnergy,
    TectonicMole,
    TectonicMoleError,
)


def make_mole(**overrides):
    """Создаёт транспорт с безопасными для большинства тестов параметрами."""
    params = {
        "name": "Тектоник",
        "mass_kg": 900.0,
        "drill_diameter_m": 2.0,
        "max_speed_kmh": 50.0,
        "energy": 100.0,
    }
    params.update(overrides)
    return TectonicMole(**params)


class TectonicPilot:
    """Тестовая обёртка пилота для сценариев в формате GWT."""

    def __init__(self, vehicle):
        self.vehicle = vehicle

    def drive(self, distance_km):
        return self.vehicle.move(distance_km, "ground")

    def bore(self, distance_km):
        return self.vehicle.move(distance_km, "tunnel")

    def swim(self, distance_km):
        return self.vehicle.move(distance_km, "water")

    def refuel(self, amount):
        return self.vehicle.refuel(amount)

    def can_overcome(self, obstacle):
        return self.vehicle.can_overcome(obstacle)


class TectonicMoleUnitTests(unittest.TestCase):
    def test_init_rejects_empty_name(self):
        """TC-01: пустое имя должно отклоняться."""
        # Arrange
        params = {
            "name": "   ",
            "mass_kg": 900.0,
            "drill_diameter_m": 2.0,
            "max_speed_kmh": 50.0,
        }

        # Act / Assert
        with self.assertRaises(ValueError):
            TectonicMole(**params)

    def test_init_rejects_nonpositive_dimensions(self):
        """TC-02: масса, диаметр бура и скорость должны быть положительными."""
        # Arrange
        fields = ("mass_kg", "drill_diameter_m", "max_speed_kmh")

        # Act / Assert
        for field in fields:
            with self.subTest(field=field):
                params = {
                    "name": "Тектоник",
                    "mass_kg": 900.0,
                    "drill_diameter_m": 2.0,
                    "max_speed_kmh": 50.0,
                }
                params[field] = 0
                with self.assertRaises(ValueError):
                    TectonicMole(**params)

    def test_init_validates_energy_and_default(self):
        """TC-03: энергия ограничена диапазоном, default равен 100."""
        # Arrange / Act / Assert
        for energy in (-1, 101):
            with self.subTest(energy=energy):
                with self.assertRaises(ValueError):
                    make_mole(energy=energy)

        self.assertEqual(make_mole().energy, 100.0)

    def test_initial_state_is_origin_and_not_drilling(self):
        """TC-04: новый транспорт начинается в начале маршрута."""
        # Arrange / Act
        mole = make_mole()

        # Assert
        self.assertEqual(mole.position_km, 0.0)
        self.assertFalse(mole.is_drilling)

    def test_move_ground_updates_state(self):
        """TC-05: поверхность использует максимальную скорость и расход 1/км."""
        # Arrange
        mole = make_mole(energy=100.0, max_speed_kmh=50.0)

        # Act
        elapsed = mole.move(20, "ground")

        # Assert
        self.assertEqual(elapsed, 0.4)
        self.assertEqual(mole.position_km, 20.0)
        self.assertEqual(mole.energy, 80.0)
        self.assertFalse(mole.is_drilling)

    def test_move_tunnel_uses_boring_rules(self):
        """TC-06: тоннель снижает скорость до 0.6 и расходует 3/км."""
        # Arrange
        mole = make_mole(energy=50.0, max_speed_kmh=40.0)

        # Act
        elapsed = mole.move(10, "tunnel")

        # Assert
        self.assertAlmostEqual(elapsed, 10 / 24)
        self.assertEqual(mole.position_km, 10.0)
        self.assertEqual(mole.energy, 20.0)
        self.assertTrue(mole.is_drilling)

    def test_move_rejects_invalid_arguments(self):
        """TC-07: движение требует положительное расстояние и известную среду."""
        # Arrange
        mole = make_mole()

        # Act / Assert
        with self.assertRaises(ValueError):
            mole.move(0, "ground")
        with self.assertRaises(ValueError):
            mole.move(1, "air")

    def test_move_water_raises_domain_error(self):
        """TC-08: транспорт не умеет перемещаться по воде."""
        # Arrange
        mole = make_mole(energy=50.0)
        before = (mole.position_km, mole.energy, mole.is_drilling)

        # Act / Assert
        with self.assertRaises(MoleCannotSwim):
            mole.move(3, "water")
        self.assertEqual(
            (mole.position_km, mole.energy, mole.is_drilling),
            before,
        )

    def test_move_rejects_insufficient_energy_without_mutation(self):
        """TC-09: нехватка энергии даёт доменную ошибку без частичного движения."""
        # Arrange
        mole = make_mole(energy=10.0)
        before = (mole.position_km, mole.energy, mole.is_drilling)

        # Act / Assert
        with self.assertRaises(MoleNoEnergy):
            mole.move(5, "tunnel")
        self.assertEqual(
            (mole.position_km, mole.energy, mole.is_drilling),
            before,
        )

    def test_move_allows_exact_zero_energy(self):
        """TC-10: последняя единица энергии может быть потрачена полностью."""
        # Arrange
        mole = make_mole(energy=50.0)

        # Act
        mole.move(50, "ground")

        # Assert
        self.assertEqual(mole.position_km, 50.0)
        self.assertEqual(mole.energy, 0.0)

    def test_calculate_energy_is_pure(self):
        """TC-11: расчёт расхода не меняет состояние и игнорирует запас энергии."""
        # Arrange
        mole = make_mole(energy=1.0)
        before = (mole.position_km, mole.energy, mole.is_drilling)

        # Act
        ground_cost = mole.calculate_energy(10, "ground")
        tunnel_cost = mole.calculate_energy(4, "tunnel")

        # Assert
        self.assertEqual(ground_cost, 10.0)
        self.assertEqual(tunnel_cost, 12.0)
        self.assertEqual(
            (mole.position_km, mole.energy, mole.is_drilling),
            before,
        )

    def test_calculate_energy_rejects_invalid_arguments(self):
        """TC-12: расчёт использует те же проверки среды и расстояния."""
        # Arrange
        mole = make_mole()

        # Act / Assert
        with self.assertRaises(ValueError):
            mole.calculate_energy(0, "ground")
        with self.assertRaises(ValueError):
            mole.calculate_energy(1, "air")
        with self.assertRaises(MoleCannotSwim):
            mole.calculate_energy(1, "water")

    def test_can_overcome_boulder_and_ravine(self):
        """TC-13: крупный бур позволяет преодолеть валун и овраг."""
        # Arrange
        mole = make_mole(drill_diameter_m=2.0, energy=40.0)
        before = (mole.position_km, mole.energy, mole.is_drilling)

        # Act
        boulder = mole.can_overcome("boulder")
        ravine = mole.can_overcome("ravine")

        # Assert
        self.assertTrue(boulder)
        self.assertTrue(ravine)
        self.assertEqual(
            (mole.position_km, mole.energy, mole.is_drilling),
            before,
        )

    def test_can_overcome_landslide_depends_on_energy(self):
        """TC-14: оползень преодолим только при достаточном запасе энергии."""
        # Arrange
        mole = make_mole(energy=29.0)

        # Act / Assert
        self.assertFalse(mole.can_overcome("landslide"))
        mole.refuel(1.0)
        self.assertTrue(mole.can_overcome("landslide"))

    def test_can_overcome_rejects_unknown_obstacle(self):
        """TC-15: список препятствий ограничен контрактом."""
        # Arrange
        mole = make_mole()

        # Act / Assert
        with self.assertRaises(ValueError):
            mole.can_overcome("wall")

    def test_refuel_adds_and_caps_energy(self):
        """TC-16: заправка увеличивает энергию, но не выше 100."""
        # Arrange
        mole = make_mole(energy=50.0)

        # Act
        mole.refuel(20)
        after_small_refuel = mole.energy
        mole.refuel(1000)

        # Assert
        self.assertEqual(after_small_refuel, 70.0)
        self.assertEqual(mole.energy, 100.0)

    def test_refuel_rejects_nonpositive_amount(self):
        """TC-17: нулевая и отрицательная заправка запрещены."""
        # Arrange
        mole = make_mole(energy=50.0)

        # Act / Assert
        for amount in (0, -1):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    mole.refuel(amount)
        self.assertEqual(mole.energy, 50.0)

    def test_get_status_returns_expected_snapshot(self):
        """TC-18: статус содержит ровно публичные поля снимка."""
        # Arrange
        mole = make_mole(energy=50.0, drill_diameter_m=1.5)
        mole.move(10, "tunnel")

        # Act
        status = mole.get_status()

        # Assert
        self.assertEqual(
            set(status),
            {"name", "energy", "position_km", "is_drilling", "drill_diameter_m"},
        )
        self.assertEqual(status["name"], "Тектоник")
        self.assertEqual(status["energy"], 20.0)
        self.assertEqual(status["position_km"], 10.0)
        self.assertTrue(status["is_drilling"])
        self.assertEqual(status["drill_diameter_m"], 1.5)

    def test_domain_exceptions_have_expected_hierarchy(self):
        """TC-19: ошибки домена отделены от стандартных ошибок параметров."""
        # Arrange / Act / Assert
        self.assertTrue(issubclass(TectonicMoleError, CrazyVehicleError))
        self.assertTrue(issubclass(MoleNoEnergy, TectonicMoleError))
        self.assertTrue(issubclass(MoleCannotSwim, TectonicMoleError))

    def test_init_accepts_lower_energy_boundary(self):
        """TC-20: нулевой запас энергии допустим при создании."""
        # Arrange / Act
        mole = make_mole(energy=0.0)

        # Assert
        self.assertEqual(mole.energy, 0.0)


class TectonicMoleScenarioTests(unittest.TestCase):
    def test_TC_21_tunnel_under_railway(self):
        """TC-21: GWT-сценарий тоннеля под железной дорогой."""
        # Given
        pilot = TectonicPilot(make_mole(energy=70.0, max_speed_kmh=50.0))

        # When / Then
        self.assertEqual(pilot.drive(10), 0.2)
        self.assertEqual(pilot.vehicle.energy, 60.0)
        self.assertFalse(pilot.vehicle.is_drilling)

        # When / Then
        self.assertEqual(pilot.bore(6), 6 / 30)
        self.assertEqual(pilot.vehicle.position_km, 16.0)
        self.assertEqual(pilot.vehicle.energy, 42.0)
        self.assertTrue(pilot.vehicle.is_drilling)

        # When / Then
        pilot.refuel(50)
        pilot.drive(4)
        self.assertEqual(pilot.vehicle.position_km, 20.0)
        self.assertEqual(pilot.vehicle.energy, 88.0)
        self.assertFalse(pilot.vehicle.is_drilling)

    def test_TC_22_escape_landslide(self):
        """TC-22: GWT-сценарий ухода от оползня."""
        # Given
        pilot = TectonicPilot(
            make_mole(
                energy=25.0,
                drill_diameter_m=1.2,
                max_speed_kmh=40.0,
            )
        )

        # When / Then
        self.assertTrue(pilot.can_overcome("boulder"))
        self.assertFalse(pilot.can_overcome("ravine"))

        # When / Then
        pilot.refuel(10)
        self.assertTrue(pilot.can_overcome("landslide"))
        pilot.drive(5)
        self.assertEqual(pilot.vehicle.energy, 30.0)
        self.assertAlmostEqual(pilot.bore(5), 5 / 24)

        # Then
        self.assertEqual(pilot.vehicle.position_km, 10.0)
        self.assertEqual(pilot.vehicle.energy, 15.0)

    def test_TC_23_emergency_energy_reserve(self):
        """TC-23: GWT-сценарий аварийного энергетического резерва."""
        # Given
        pilot = TectonicPilot(make_mole(energy=20.0))

        # When / Then
        pilot.bore(6)
        self.assertEqual(pilot.vehicle.position_km, 6.0)
        self.assertEqual(pilot.vehicle.energy, 2.0)
        self.assertTrue(pilot.vehicle.is_drilling)

        # When / Then
        with self.assertRaises(MoleNoEnergy):
            pilot.bore(1)
        self.assertEqual(pilot.vehicle.position_km, 6.0)
        self.assertEqual(pilot.vehicle.energy, 2.0)

        # When / Then
        pilot.refuel(10)
        pilot.drive(2)
        self.assertEqual(pilot.vehicle.position_km, 8.0)
        self.assertEqual(pilot.vehicle.energy, 10.0)
        self.assertFalse(pilot.vehicle.is_drilling)

    def test_TC_24_water_on_route(self):
        """TC-24: GWT-сценарий встречи с водой на маршруте."""
        # Given
        pilot = TectonicPilot(make_mole(energy=50.0))

        # When / Then
        pilot.drive(10)
        with self.assertRaises(MoleCannotSwim):
            pilot.swim(3)
        self.assertEqual(pilot.vehicle.position_km, 10.0)
        self.assertEqual(pilot.vehicle.energy, 40.0)

        # When / Then
        pilot.drive(5)
        self.assertEqual(pilot.vehicle.position_km, 15.0)
        self.assertEqual(pilot.vehicle.energy, 35.0)


if __name__ == "__main__":
    unittest.main()
