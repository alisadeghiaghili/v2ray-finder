# src/v2ray_finder/gui/main_window.py
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import V2RayServerFinder


class WorkerThread(QThread):
    """Background thread for fetching servers to avoid freezing GUI."""

    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, token=None, use_search=False):
        super().__init__()
        self.token = token
        self.use_search = use_search

    def run(self):
        try:
            self.progress.emit("Initializing...")
            finder = V2RayServerFinder(token=self.token)

            self.progress.emit("Fetching from known sources...")
            servers = finder.get_servers_from_known_sources()

            if self.use_search:
                self.progress.emit("Searching GitHub repositories...")
                github_servers = finder.get_servers_from_github()
                servers.extend(github_servers)
                servers = list(dict.fromkeys(servers))

            self.progress.emit(f"Found {len(servers)} unique servers")
            self.finished.emit(servers)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main GUI window for v2ray-finder."""

    def __init__(self):
        super().__init__()
        self.servers = []
        self.init_ui()

    def init_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("v2ray-finder")
        self.setGeometry(100, 100, 1000, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Top controls row
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("GitHub token (optional)")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setMinimumWidth(250)
        controls_layout.addWidget(self.token_input)

        self.search_checkbox = QCheckBox("Enable GitHub Search")
        self.search_checkbox.setToolTip("Slower but finds more repositories")
        controls_layout.addWidget(self.search_checkbox)
        controls_layout.addStretch()

        controls_layout.addWidget(QLabel("Limit:"))
        self.limit_spinbox = QSpinBox()
        self.limit_spinbox.setMinimum(0)
        self.limit_spinbox.setMaximum(5000)
        self.limit_spinbox.setValue(0)
        self.limit_spinbox.setSpecialValueText("No limit")
        controls_layout.addWidget(self.limit_spinbox)

        main_layout.addLayout(controls_layout)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.fetch_btn = QPushButton("🔍 Fetch Servers")
        self.fetch_btn.clicked.connect(self.fetch_servers)
        buttons_layout.addWidget(self.fetch_btn)

        self.save_btn = QPushButton("💾 Save to File")
        self.save_btn.clicked.connect(self.save_servers)
        self.save_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_btn)

        self.copy_btn = QPushButton("📋 Copy Selected")
        self.copy_btn.clicked.connect(self.copy_selected)
        self.copy_btn.setEnabled(False)
        buttons_layout.addWidget(self.copy_btn)

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_table)
        buttons_layout.addWidget(self.clear_btn)

        main_layout.addLayout(buttons_layout)

        # Status label
        self.status_label = QLabel("Ready to fetch servers")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold;")
        main_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Stats label
        self.stats_label = QLabel("")
        stats_font = QFont()
        stats_font.setBold(True)
        self.stats_label.setFont(stats_font)
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet(
            "padding: 8px; background-color: #f0f0f0; border-radius: 4px;"
        )
        main_layout.addWidget(self.stats_label)

        # Servers table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "Protocol", "Config"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)

        central_widget.setLayout(main_layout)

    def fetch_servers(self):
        """Start background fetch process."""
        if self.fetch_btn.text() == "🔄 Fetching...":
            return

        self.fetch_btn.setText("🔄 Fetching...")
        self.fetch_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        token = self.token_input.text().strip() or None
        use_search = self.search_checkbox.isChecked()

        self.worker = WorkerThread(token=token, use_search=use_search)
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()

    def update_status(self, message):
        """Update status label."""
        self.status_label.setText(message)

    def on_fetch_finished(self, servers):
        """Handle successful fetch."""
        self.servers = servers

        limit = self.limit_spinbox.value()
        display_servers = servers[:limit] if limit > 0 else servers

        self.table.setRowCount(len(display_servers))

        for i, server in enumerate(display_servers):
            protocol = server.split("://")[0] if "://" in server else "unknown"

            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(protocol))
            self.table.setItem(i, 2, QTableWidgetItem(server))

        self.update_stats(servers)

        self.fetch_btn.setText("🔍 Fetch Servers")
        self.fetch_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✅ Fetched {len(servers)} unique servers")

    def on_fetch_error(self, error):
        """Handle fetch error."""
        self.fetch_btn.setText("🔍 Fetch Servers")
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Error: {error}")
        QMessageBox.critical(self, "Fetch Error", f"Failed to fetch servers:\n{error}")

    def update_stats(self, servers):
        """Update statistics display."""
        protocols = {}
        for server in servers:
            protocol = server.split("://")[0] if "://" in server else "unknown"
            protocols[protocol] = protocols.get(protocol, 0) + 1

        stats_text = f"Total: {len(servers)} servers | "
        stats_parts = []
        for protocol, count in sorted(
            protocols.items(), key=lambda x: x[1], reverse=True
        ):
            stats_parts.append(f"{protocol}: {count}")
        stats_text += " | ".join(stats_parts)

        self.stats_label.setText(stats_text)

    def save_servers(self):
        """Save all (or limited) servers to file."""
        if not self.servers:
            QMessageBox.warning(self, "No Data", "No servers loaded. Fetch first.")
            return

        limit = self.limit_spinbox.value()
        servers_to_save = self.servers[:limit] if limit > 0 else self.servers

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save V2Ray Servers",
            "v2ray_servers.txt",
            "Text Files (*.txt);;All Files (*)",
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    for server in servers_to_save:
                        f.write(f"{server}\n")

                QMessageBox.information(
                    self,
                    "Saved!",
                    f"Saved {len(servers_to_save)} servers to:\n{filename}",
                )
                self.status_label.setText(f"💾 Saved {len(servers_to_save)} servers")
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error", f"Failed to save file:\n{str(e)}"
                )

    def copy_selected(self):
        """Copy selected rows to clipboard."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self, "Nothing Selected", "Please select rows in the table."
            )
            return

        selected_rows = set(item.row() for item in selected_items)
        configs = []

        for row in sorted(selected_rows):
            config_item = self.table.item(row, 2)
            if config_item:
                configs.append(config_item.text())

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(configs))

        self.status_label.setText(f"📋 Copied {len(configs)} configs to clipboard")

    def clear_table(self):
        """Clear table and reset UI."""
        self.table.setRowCount(0)
        self.stats_label.setText("")
        self.servers = []
        self.status_label.setText("🗑️ Table cleared")
        self.save_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)


def launch():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("v2ray-finder")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
