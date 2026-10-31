package com.zishan.islamicclock

import org.junit.Assert.assertThrows
import org.junit.Test

class PrayerSettingsTest {
    @Test
    fun rejectsInvalidCoordinates() {
        assertThrows(IllegalArgumentException::class.java) {
            PrayerSettings(latitude = 91.0)
        }
    }

    @Test
    fun rejectsInvalidAdjustment() {
        assertThrows(IllegalArgumentException::class.java) {
            PrayerSettings(adjustments = mapOf("Fajr" to 181))
        }
    }
}
