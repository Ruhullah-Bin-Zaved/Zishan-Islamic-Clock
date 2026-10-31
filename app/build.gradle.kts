plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.zishan.islamicclock"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.zishan.islamicclock"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }
}

dependencies {
    implementation("com.batoulapps.adhan:adhan:1.2.1")
    testImplementation("junit:junit:4.13.2")
}

kotlin {
    jvmToolchain(17)
}
