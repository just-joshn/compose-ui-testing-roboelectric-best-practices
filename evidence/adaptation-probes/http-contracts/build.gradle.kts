plugins { kotlin("jvm") version "2.2.10" }
repositories { mavenCentral() }
kotlin { jvmToolchain(17) }
dependencies {
 testImplementation("junit:junit:4.13.2")
 testImplementation("com.squareup.okhttp3:okhttp:4.12.0")
 testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
 testImplementation("org.json:json:20240303")
}
tasks.test { useJUnit(); testLogging { events("passed", "failed") } }
