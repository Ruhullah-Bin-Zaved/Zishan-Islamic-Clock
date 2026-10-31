package com.zishan.islamicclock

import android.content.Context
import java.time.ZoneId

enum class CalculationMethodOption { MUSLIM_WORLD_LEAGUE, KARACHI, EGYPTIAN, NORTH_AMERICA, SINGAPORE }
enum class AsrMethod { SHAFI, HANAFI }
enum class HighLatitudeOption { MIDDLE_OF_THE_NIGHT, SEVENTH_OF_THE_NIGHT, TWILIGHT_ANGLE }

data class PrayerSettings(
    val latitude: Double = 23.8103,
    val longitude: Double = 90.4125,
    val zoneId: String = ZoneId.systemDefault().id,
    val method: CalculationMethodOption = CalculationMethodOption.MUSLIM_WORLD_LEAGUE,
    val asrMethod: AsrMethod = AsrMethod.HANAFI,
    val highLatitude: HighLatitudeOption = HighLatitudeOption.MIDDLE_OF_THE_NIGHT,
    val adjustments: Map<String, Int> = emptyMap()
) {
    init {
        require(latitude in -90.0..90.0)
        require(longitude in -180.0..180.0)
        ZoneId.of(zoneId)
        require(adjustments.keys.all { it in PrayerCalculator.prayerNames })
        require(adjustments.values.all { it in -180..180 })
    }
}

class PrayerSettingsStore(context: Context) {
    private val preferences = context.getSharedPreferences("prayer_settings", Context.MODE_PRIVATE)

    fun load(): PrayerSettings {
        return runCatching {
            PrayerSettings(
                latitude = preferences.getString("latitude", "23.8103")!!.toDouble(),
                longitude = preferences.getString("longitude", "90.4125")!!.toDouble(),
                zoneId = preferences.getString("zoneId", ZoneId.systemDefault().id)!!,
                method = CalculationMethodOption.valueOf(preferences.getString("method", CalculationMethodOption.MUSLIM_WORLD_LEAGUE.name)!!),
                asrMethod = AsrMethod.valueOf(preferences.getString("asr", AsrMethod.HANAFI.name)!!),
                highLatitude = HighLatitudeOption.valueOf(preferences.getString("highLatitude", HighLatitudeOption.MIDDLE_OF_THE_NIGHT.name)!!),
                adjustments = PrayerCalculator.prayerNames.associateWith { preferences.getInt("adjust_$it", 0) }
                    .filterValues { it != 0 }
            )
        }.getOrElse { PrayerSettings() }
    }

    fun save(settings: PrayerSettings) {
        settings.requireValid()
        preferences.edit().apply {
            putString("latitude", settings.latitude.toString())
            putString("longitude", settings.longitude.toString())
            putString("zoneId", settings.zoneId)
            putString("method", settings.method.name)
            putString("asr", settings.asrMethod.name)
            putString("highLatitude", settings.highLatitude.name)
            PrayerCalculator.prayerNames.forEach { putInt("adjust_$it", settings.adjustments[it] ?: 0) }
            apply()
        }
    }
}

fun PrayerSettings.requireValid() {
    require(latitude in -90.0..90.0 && longitude in -180.0..180.0)
    ZoneId.of(zoneId)
}
