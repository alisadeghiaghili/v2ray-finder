package com.v2rayfinder.network

import com.v2rayfinder.model.ServerConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class ConfigFetcher {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val sources = listOf(
        "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub1.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/Eternity.txt",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/splitted/mixed",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/main/vless.txt",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/main/vmess.txt",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/main/trojan.txt",
    )

    private val configPattern = Regex(
        "(?:vmess|vless|trojan|ss|ssr)://[A-Za-z0-9+/=_\\-@:.?&#%]+",
        RegexOption.IGNORE_CASE
    )

    suspend fun fetchConfigs(): List<ServerConfig> = withContext(Dispatchers.IO) {
        val allConfigs = mutableListOf<String>()

        for (source in sources) {
            try {
                val configs = fetchFromSource(source)
                allConfigs.addAll(configs)
            } catch (e: Exception) {
                // Skip failed sources
            }
        }

        // Deduplicate
        val unique = allConfigs.distinct()

        // Convert to ServerConfig
        unique.map { ServerConfig.fromUri(it) }
            .sortedByDescending { it.antiCensorshipLevel }
    }

    private fun fetchFromSource(url: String): List<String> {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "v2ray-finder-android/2.0")
            .build()

        val response = client.newCall(request).execute()
        val body = response.body?.string() ?: return emptyList()

        return configPattern.findAll(body)
            .map { it.value }
            .toList()
    }

    suspend fun checkLatency(host: String, port: Int): Double? = withContext(Dispatchers.IO) {
        try {
            val startTime = System.currentTimeMillis()
            val socket = java.net.Socket()
            socket.connect(java.net.InetSocketAddress(host, port), 5000)
            socket.close()
            val latency = System.currentTimeMillis() - startTime
            latency.toDouble()
        } catch (e: Exception) {
            null
        }
    }
}
