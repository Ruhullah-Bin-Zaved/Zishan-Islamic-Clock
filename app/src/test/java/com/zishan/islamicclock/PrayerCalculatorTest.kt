package com.zishan.islamicclock

import java.time.LocalDate
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PrayerCalculatorTest {
    @Test
    fun calculatesFiveLocalPrayerTimesOffline() {
        val date = LocalDate.of(2024, 6, 15)
        val settings = PrayerSettings(zoneId = "Asia/Dhaka")
        val result = PrayerCalculator().calculate(date, settings)

        assertEquals(5, result.size)
        assertEquals(PrayerCalculator.prayerNames, result.map { it.name })
        assertTrue(result.all { it.calculated.zone == ZoneId.of("Asia/Dhaka") })
    }

    @Test
    fun appliesManualAdjustmentWithoutChangingCalculatedValue() {
        val settings = PrayerSettings(
            zoneId = "Asia/Dhaka",
            adjustments = mapOf("Fajr" to 3)
        )
        val fajr = PrayerCalculator().calculate(LocalDate.of(2024, 6, 15), settings).first()

        assertEquals(fajr.calculated.plusMinutes(3), fajr.adjusted)
    }
}
