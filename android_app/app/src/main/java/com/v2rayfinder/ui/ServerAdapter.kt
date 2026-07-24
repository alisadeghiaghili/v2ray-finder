package com.v2rayfinder.ui

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.cardview.widget.CardView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.v2rayfinder.R
import com.v2rayfinder.model.ServerConfig

class ServerAdapter(
    private val onItemClick: (ServerConfig) -> Unit
) : ListAdapter<ServerConfig, ServerAdapter.ViewHolder>(DiffCallback) {

    private var selectedIndex: Int = -1

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_server, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val server = getItem(position)
        holder.bind(server, position == selectedIndex)

        holder.itemView.setOnClickListener {
            val oldSelected = selectedIndex
            selectedIndex = if (selectedIndex == position) -1 else position

            if (oldSelected >= 0) notifyItemChanged(oldSelected)
            notifyItemChanged(position)

            onItemClick(getItem(position))
        }
    }

    fun getSelectedServer(): ServerConfig? {
        return if (selectedIndex >= 0) getItem(selectedIndex) else null
    }

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: CardView = itemView.findViewById(R.id.card)
        private val tvProtocol: TextView = itemView.findViewById(R.id.tvProtocol)
        private val tvGrade: TextView = itemView.findViewById(R.id.tvGrade)
        private val tvHost: TextView = itemView.findViewById(R.id.tvHost)
        private val tvLevel: TextView = itemView.findViewById(R.id.tvLevel)
        private val tvLatency: TextView = itemView.findViewById(R.id.tvLatency)

        fun bind(server: ServerConfig, isSelected: Boolean) {
            tvProtocol.text = server.protocol
            tvGrade.text = server.antiCensorshipGrade
            tvHost.text = "${server.host}:${server.port}"
            tvLevel.text = "Level ${server.antiCensorshipLevel}"

            tvLatency.text = server.latencyMs?.let { "${it.toInt()}ms" } ?: "n/a"

            // Grade color
            val gradeColor = when (server.antiCensorshipLevel) {
                5 -> Color.parseColor("#4CAF50") // Green
                4 -> Color.parseColor("#8BC34A") // Light green
                3 -> Color.parseColor("#FFC107") // Amber
                2 -> Color.parseColor("#FF9800") // Orange
                else -> Color.parseColor("#F44336") // Red
            }
            tvGrade.setBackgroundColor(gradeColor)

            // Selection highlight
            card.setCardBackgroundColor(
                if (isSelected) Color.parseColor("#E3F2FD") else Color.WHITE
            )
        }
    }

    companion object DiffCallback : DiffUtil.ItemCallback<ServerConfig>() {
        override fun areItemsTheSame(oldItem: ServerConfig, newItem: ServerConfig): Boolean {
            return oldItem.uri == newItem.uri
        }

        override fun areContentsTheSame(oldItem: ServerConfig, newItem: ServerConfig): Boolean {
            return oldItem == newItem
        }
    }
}
