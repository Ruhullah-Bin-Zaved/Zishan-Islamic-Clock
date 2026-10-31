package com.zishan.islamicclock

import com.batoulapps.adhan.CalculationMethod
import com.batoulapps.adhan.Coordinates
import com.batoulapps.adhan.DateComponents
import com.batoulapps.adhan.HighLatitudeRule
import com.batoulapps.adhan.Madhab
import com.batoulapps.adhan.PrayerTimes
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import java.util.Date

data class PrayerTime(val name: String, val calculated: ZonedDateTime, val adjusted: ZonedDateTime)

class PrayerCalculator {
    fun calculate(date: LocalDate, settings: PrayerSettings): List<PrayerTime> {
        settings.requireValid()
        val parameters = method(settings.method).getParameters().apply {
            madhab = if (settings.asrMethod == AsrMethod.HANAFI) Madhab.HANAFI else Madhab.SHAFI
            highLatitudeRule = when (settings.highLatitude) {
                HighLatitudeOption.MIDDLE_OF_THE_NIGHT -> HighLatitudeRule.MIDDLE_OF_THE_NIGHT
                HighLatitudeOption.SEVENTH_OF_THE_NIGHT -> HighLatitudeRule.SEVENTH_OF_THE_NIGHT
                HighLatitudeOption.TWILIGHT_ANGLE -> HighLatitudeRule.TWILIGHT_ANGLE
            }
        }
        val times = PrayerTimes(
            Coordinates(settings.latitude, settings.longitude),
            DateComponents(date.year, date.monthValue, date.dayOfMonth),
            parameters
        )
        val zone = ZoneId.of(settings.zoneId)
        return listOf(
            "Fajr" to times.fajr,
            "Dhuhr" to times.dhuhr,
            "Asr" to times.asr,
            "Maghrib" to times.maghrib,
            "Isha" to times.isha
        ).map { (name, value) ->
            val calculated = value.toZonedDateTime(zone)
            val adjusted = calculated.plusMinutes(settings.adjustments[name]?.toLong() ?: 0)
            PrayerTime(name, calculated, adjusted)
        }
    }

    private fun Date.toZonedDateTime(zone: ZoneId): ZonedDateTime =
        toInstant().atZone(zone)

    private fun method(option: CalculationMethodOption): CalculationMethod = when (option) {
        CalculationMethodOption.MUSLIM_WORLD_LEAGUE -> CalculationMethod.MUSLIM_WORLD_LEAGUE
        CalculationMethodOption.KARACHI -> CalculationMethod.KARACHI
        CalculationMethodOption.EGYPTIAN -> CalculationMethod.EGYPTIAN
        CalculationMethodOption.NORTH_AMERICA -> CalculationMethod.NORTH_AMERICA
        CalculationMethodOption.SINGAPORE -> CalculationMethod.SINGAPORE
    }

    companion object {
        val prayerNames = listOf("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha")
    }
}
