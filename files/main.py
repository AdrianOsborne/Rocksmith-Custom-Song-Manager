import os
import random
import shutil
import json
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QDialog, QInputDialog, QMessageBox, QSplashScreen
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap

CONFIG_FILE = "files/config.json"

class LoadingScreen(QSplashScreen):
    def __init__(self, message="Loading..."):
        super().__init__(QPixmap(400, 300))
        self.showMessage(message, Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

class WorkerThread(QThread):
    update_toggle_signal = pyqtSignal(str, bool)
    finished_signal = pyqtSignal()

    def __init__(self, files, enable, batch=False):
        super().__init__()
        self.files = files
        self.enable = enable
        self.batch = batch

    def run(self):
        for file in self.files:
            print(f"Toggling file: {file}")
            self.toggle_file(file, self.enable)
            if not self.batch:
                self.update_toggle_signal.emit(file, self.enable)
        self.finished_signal.emit()

    def toggle_file(self, file, enable):
        if enable:
            new_file = file.replace(".disabled", ".psarc")
        else:
            new_file = file.replace(".psarc", ".disabled")
        os.rename(file, new_file)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocksmith DLC Manager")
        self.setGeometry(100, 100, 800, 600)

        # Initial state
        self.dlc_folder = None

        # Load previous config
        self.load_config()

        # Main layout
        layout = QVBoxLayout()

        # DLC folder selection
        self.dlc_folder_label = QLabel("No DLC folder selected")
        layout.addWidget(self.dlc_folder_label)
        select_dlc_button = QPushButton("Select DLC Folder")
        select_dlc_button.clicked.connect(self.select_dlc_folder)
        layout.addWidget(select_dlc_button)

        # DLC management buttons
        self.enable_all_button = QPushButton("Enable All DLC")
        self.enable_all_button.setEnabled(False)
        self.enable_all_button.clicked.connect(self.handle_enable_all)
        layout.addWidget(self.enable_all_button)

        self.disable_all_button = QPushButton("Disable All DLC")
        self.disable_all_button.setEnabled(False)
        self.disable_all_button.clicked.connect(self.handle_disable_all)
        layout.addWidget(self.disable_all_button)

        self.enable_random_button = QPushButton("Enable Random DLC")
        self.enable_random_button.setEnabled(False)
        self.enable_random_button.clicked.connect(self.handle_enable_random)
        layout.addWidget(self.enable_random_button)

        self.reset_data_button = QPushButton("Reset All Data")
        self.reset_data_button.setEnabled(False)
        self.reset_data_button.clicked.connect(self.handle_reset_all_data)
        layout.addWidget(self.reset_data_button)

        # DLC directory tree
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search directories...")
        self.search_bar.textChanged.connect(self.filter_tree)
        self.search_bar.setEnabled(False)
        layout.addWidget(self.search_bar)

        self.directory_tree = QTreeWidget()
        self.directory_tree.setHeaderLabel("DLC Directories")
        self.directory_tree.itemDoubleClicked.connect(self.edit_directory)
        self.directory_tree.setEnabled(False)
        layout.addWidget(self.directory_tree)

        # Check if we have a previously set DLC folder
        if self.dlc_folder:
            self.dlc_folder_label.setText(f"DLC Folder: {self.dlc_folder}")
            self.load_directory_tree()
            self.enable_all_button.setEnabled(True)
            self.disable_all_button.setEnabled(True)
            self.enable_random_button.setEnabled(True)
            self.reset_data_button.setEnabled(True)
            self.search_bar.setEnabled(True)
            self.directory_tree.setEnabled(True)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def select_dlc_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DLC Folder")
        if folder:
            self.dlc_folder = folder
            self.dlc_folder_label.setText(f"DLC Folder: {self.dlc_folder}")
            self.save_config()
            self.load_directory_tree()
            self.enable_all_button.setEnabled(True)
            self.disable_all_button.setEnabled(True)
            self.enable_random_button.setEnabled(True)
            self.reset_data_button.setEnabled(True)
            self.search_bar.setEnabled(True)
            self.directory_tree.setEnabled(True)

    def load_directory_tree(self):
        self.show_loading_screen()
        self.directory_tree.clear()
        if self.dlc_folder:
            root_item = QTreeWidgetItem([os.path.basename(self.dlc_folder)])
            root_item.setData(0, Qt.UserRole, self.dlc_folder)
            self.directory_tree.addTopLevelItem(root_item)
            self.add_subdirectories(root_item, self.dlc_folder)
        self.loading_screen.close()

    def add_subdirectories(self, tree_item, path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                sub_item = QTreeWidgetItem([item])
                sub_item.setData(0, Qt.UserRole, item_path)
                tree_item.addChild(sub_item)
                self.add_subdirectories(sub_item, item_path)

    def filter_tree(self):
        search_text = self.search_bar.text().lower()
        self.filter_tree_item(self.directory_tree.invisibleRootItem(), search_text)

    def filter_tree_item(self, item, search_text):
        match = search_text in item.text(0).lower()
        for i in range(item.childCount()):
            child = item.child(i)
            child_match = self.filter_tree_item(child, search_text)
            match = match or child_match
        item.setHidden(not match)
        return match

    def handle_enable_all(self):
        files = self.get_all_dlc_files()
        self.start_worker_thread(files, enable=True, batch=True)

    def handle_disable_all(self):
        files = self.get_all_dlc_files()
        self.start_worker_thread(files, enable=False, batch=True)

    def handle_enable_random(self):
        x, ok = QInputDialog.getInt(self, "Enable Random DLC", "Enter the number of DLCs to enable:")
        if ok:
            all_files = self.get_all_dlc_files()
            random_files = random.sample(all_files, min(x, len(all_files)))
            self.start_worker_thread(random_files, enable=True, batch=True)

    def handle_reset_all_data(self):
        self.show_loading_screen()
        files = self.get_all_dlc_files()
        self.start_worker_thread(files, enable=True, batch=True)
        self.dlc_folder = None
        self.dlc_folder_label.setText("No DLC folder selected")
        self.directory_tree.clear()
        self.enable_all_button.setEnabled(False)
        self.disable_all_button.setEnabled(False)
        self.enable_random_button.setEnabled(False)
        self.reset_data_button.setEnabled(False)
        self.search_bar.setEnabled(False)
        self.directory_tree.setEnabled(False)
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.loading_screen.close()

    def edit_directory(self, item, column):
        directory_path = item.data(0, Qt.UserRole)
        if directory_path:
            edit_all = QMessageBox.question(
                self, "Edit Directory",
                "Do you want to edit all subdirectories as well?",
                QMessageBox.Yes | QMessageBox.No
            )
            if edit_all == QMessageBox.Yes:
                directories = [directory_path]
                for root, dirs, files in os.walk(directory_path):
                    directories.extend([os.path.join(root, d) for d in dirs])
            else:
                directories = [directory_path]

            self.show_directory_editor(directories)

    def show_directory_editor(self, directories):
        self.hide()
        self.editor_window = DirectoryEditorWindow(directories, self)
        self.editor_window.finished_signal.connect(self.show)
        self.editor_window.show()

    def get_all_dlc_files(self):
        dlc_files = []
        for root, dirs, files in os.walk(self.dlc_folder):
            for file in files:
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    dlc_files.append(os.path.join(root, file))
        return dlc_files

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.dlc_folder = config.get("dlc_folder")

    def save_config(self):
        config = {"dlc_folder": self.dlc_folder}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

    def start_worker_thread(self, files, enable, batch=False):
        self.show_loading_screen()
        self.worker_thread = WorkerThread(files, enable, batch)
        self.worker_thread.update_toggle_signal.connect(self.update_toggle_box)
        self.worker_thread.finished_signal.connect(self.worker_thread_finished)
        self.worker_thread.start()

    def update_toggle_box(self, file, enabled):
        # Implement logic to update the toggle box associated with the file
        print(f"Updating toggle box for {file} to {'enabled' if enabled else 'disabled'}")

    def worker_thread_finished(self):
        self.loading_screen.close()
        print("Worker thread finished")

    def show_loading_screen(self):
        self.loading_screen = LoadingScreen()
        self.loading_screen.show()

class DirectoryEditorWindow(QDialog):
    finished_signal = pyqtSignal()

    def __init__(self, directories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Directory")
        self.setGeometry(100, 100, 800, 600)  # Changed window size to span entire length
        self.directories = directories

        layout = QVBoxLayout()

        # Search bar for files
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.textChanged.connect(self.filter_files)
        layout.addWidget(self.search_bar)

        # Table of DLC files
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["File Name", "Enabled"])
        self.table.horizontalHeader().setStretchLastSection(True)  # Make table span entire window width
        self.load_files()
        layout.addWidget(self.table)

        # Buttons for enabling/disabling all and random files
        button_layout = QHBoxLayout()

        enable_all_button = QPushButton("Enable All")
        enable_all_button.clicked.connect(self.handle_enable_all)
        button_layout.addWidget(enable_all_button)

        disable_all_button = QPushButton("Disable All")
        disable_all_button.clicked.connect(self.handle_disable_all)
        button_layout.addWidget(disable_all_button)

        enable_random_button = QPushButton("Enable Random")
        enable_random_button.clicked.connect(self.handle_enable_random)
        button_layout.addWidget(enable_random_button)

        back_button = QPushButton("Back")
        back_button.clicked.connect(self.close)
        button_layout.addWidget(back_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_files(self):
        self.table.setRowCount(0)
        for directory in self.directories:
            for file in os.listdir(directory):
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    self.add_file_row(directory, file)

    def add_file_row(self, directory, file):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        file_item = QTableWidgetItem(file)
        file_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 0, file_item)

        enable_checkbox = QCheckBox()
        enable_checkbox.setChecked(file.endswith(".psarc"))
        enable_checkbox.stateChanged.connect(
            lambda state, dir=directory, fname=file: self.toggle_file(dir, fname, state == Qt.Checked)
        )
        self.table.setCellWidget(row_position, 1, enable_checkbox)

    def toggle_file(self, directory, file, enable):
        old_file_path = os.path.join(directory, file)
        if enable:
            new_file_path = old_file_path.replace(".disabled", ".psarc")
        else:
            new_file_path = old_file_path.replace(".psarc", ".disabled")
        os.rename(old_file_path, new_file_path)
        print(f"Toggled file {old_file_path} to {new_file_path}")
        self.load_files()

    def handle_enable_all(self):
        files = self.get_all_files()
        self.start_worker_thread(files, enable=True, batch=False)

    def handle_disable_all(self):
        files = self.get_all_files()
        self.start_worker_thread(files, enable=False, batch=False)

    def handle_enable_random(self):
        x, ok = QInputDialog.getInt(self, "Enable Random Files", "Enter the number of files to enable:")
        if ok:
            all_files = self.get_all_files()
            random_files = random.sample(all_files, min(x, len(all_files)))
            self.start_worker_thread(random_files, enable=True, batch=False)

    def get_all_files(self):
        files = []
        for directory in self.directories:
            for file in os.listdir(directory):
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    files.append(os.path.join(directory, file))
        return files

    def start_worker_thread(self, files, enable, batch=False):
        self.worker_thread = WorkerThread(files, enable, batch)
        self.worker_thread.update_toggle_signal.connect(self.update_toggle_box)
        self.worker_thread.finished_signal.connect(self.worker_thread_finished)
        self.worker_thread.start()

    def update_toggle_box(self, file, enabled):
        # Implement logic to update the toggle box associated with the file
        print(f"Updating toggle box for {file} to {'enabled' if enabled else 'disabled'}")

    def worker_thread_finished(self):
        print("Worker thread finished")
        self.load_files()

    def filter_files(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            file_item = self.table.item(row, 0)
            file_name = file_item.text().lower()
            match = search_text in file_name
            self.table.setRowHidden(row, not match)

    def closeEvent(self, event):
        self.finished_signal.emit()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
