package com.v2rayfinder

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.v2rayfinder.databinding.ActivityMainBinding
import com.v2rayfinder.model.ServerConfig
import com.v2rayfinder.network.ConfigFetcher
import com.v2rayfinder.ui.ServerAdapter
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: ServerAdapter
    private val fetcher = ConfigFetcher()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupRecyclerView()
        setupSwipeRefresh()
        setupButtons()

        loadServers()
    }

    private fun setupRecyclerView() {
        adapter = ServerAdapter { server ->
            connectToServer(server)
        }
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter
    }

    private fun setupSwipeRefresh() {
        binding.swipeRefresh.setOnRefreshListener {
            loadServers()
        }
    }

    private fun setupButtons() {
        binding.btnRefresh.setOnClickListener {
            loadServers()
        }

        binding.btnConnect.setOnClickListener {
            val selected = adapter.getSelectedServer()
            if (selected != null) {
                connectToServer(selected)
            } else {
                Toast.makeText(this, "Select a server first", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnDisconnect.setOnClickListener {
            disconnect()
        }
    }

    private fun loadServers() {
        binding.progressBar.visibility = View.VISIBLE
        binding.tvStatus.text = "Fetching servers..."

        lifecycleScope.launch {
            try {
                val configs = fetcher.fetchConfigs()
                adapter.submitList(configs)
                binding.tvStatus.text = "Found ${configs.size} servers"
            } catch (e: Exception) {
                binding.tvStatus.text = "Error: ${e.message}"
                Toast.makeText(this@MainActivity, "Failed to load servers", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false
            }
        }
    }

    private fun connectToServer(server: ServerConfig) {
        binding.tvStatus.text = "Connecting to ${server.protocol}..."
        binding.btnConnect.isEnabled = false

        lifecycleScope.launch {
            try {
                // TODO: Implement actual VPN connection via xray
                binding.tvStatus.text = "Connected to ${server.protocol}"
                binding.btnConnect.isEnabled = false
                binding.btnDisconnect.isEnabled = true
                Toast.makeText(this@MainActivity, "Connected!", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                binding.tvStatus.text = "Connection failed: ${e.message}"
                binding.btnConnect.isEnabled = true
            }
        }
    }

    private fun disconnect() {
        // TODO: Implement disconnect
        binding.tvStatus.text = "Disconnected"
        binding.btnConnect.isEnabled = true
        binding.btnDisconnect.isEnabled = false
        Toast.makeText(this, "Disconnected", Toast.LENGTH_SHORT).show()
    }
}
