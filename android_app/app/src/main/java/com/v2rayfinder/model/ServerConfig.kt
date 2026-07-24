package com.v2rayfinder.model

data class ServerConfig(
    val uri: String,
    val protocol: String,
    val host: String,
    val port: Int,
    val antiCensorshipLevel: Int,
    val antiCensorshipGrade: String,
    val latencyMs: Double? = null,
    val source: String = "",
    val isSelected: Boolean = false
) {
    companion object {
        fun fromUri(uri: String): ServerConfig {
            val protocol = uri.split("://").firstOrNull()?.uppercase() ?: "UNKNOWN"
            val host = extractHost(uri)
            val port = extractPort(uri)
            val level = scanAntiCensorship(uri)
            val grade = when (level) {
                5 -> "A+"
                4 -> "A"
                3 -> "B"
                2 -> "C"
                else -> "D"
            }

            return ServerConfig(
                uri = uri,
                protocol = protocol,
                host = host,
                port = port,
                antiCensorshipLevel = level,
                antiCensorshipGrade = grade
            )
        }

        private fun extractHost(uri: String): String {
            return try {
                val withoutScheme = uri.substringAfter("://")
                val withoutParams = withoutScheme.split("?").first()
                val withoutFragment = withoutParams.split("#").first()
                val hostPort = withoutFragment.substringAfter("@").substringBeforeLast(":")
                hostPort.removeSurrounding("[", "]")
            } catch (e: Exception) {
                "unknown"
            }
        }

        private fun extractPort(uri: String): Int {
            return try {
                val withoutScheme = uri.substringAfter("://")
                val withoutParams = withoutScheme.split("?").first()
                val withoutFragment = withoutParams.split("#").first()
                val hostPort = withoutFragment.substringAfter("@").substringBeforeLast(":")
                hostPort.substringAfterLast(":").toInt()
            } catch (e: Exception) {
                443
            }
        }

        private fun scanAntiCensorship(uri: String): Int {
            val lower = uri.lowercase()
            return when {
                "security=reality" in lower -> 5
                "xtls-rprx-vision" in lower -> 5
                "security=xtls" in lower -> 5
                "type=ws" in lower && "security=tls" in lower -> 4
                "type=grpc" in lower && "security=tls" in lower -> 4
                "type=mkcp" in lower -> 3
                "type=h2" in lower && "security=tls" in lower -> 3
                "security=tls" in lower -> 2
                else -> 1
            }
        }
    }
}
