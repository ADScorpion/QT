import pyodbc

from PySide2 import QtCore, QtWidgets
from PySide2.QtSql import QSqlTableModel, QSqlQuery, QSqlDatabase

from ui import SQL_mainWindows
from settings import *


class MySQLViewerForm(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MySQLViewerForm, self).__init__(parent)
        self.ui = SQL_mainWindows.Ui_MainWindow()
        self.ui.setupUi(self)

        self.driver_name = ""
        self.server_name = ""
        self.port = ""
        self.db_name = ""

        self.sql_login = None
        self.sql_pass = None

        # подключаем событийность (сигналы)
        # кнопки
        self.ui.exit_action.triggered.connect(self.closeEvent)
        self.ui.radio_windows_authentication.toggled.connect(self.change_to_auth)
        self.ui.button_connect.clicked.connect(self.connect_to_DB)
        self.ui.button_show_table.clicked.connect(self.show_requested_table)

        self.connection = None

        self.model = QSqlTableModel()

        self.init_cred()

    def init_cred(self):
        self.ui.lineEdit_driver.setText(CON_DRV)
        self.ui.lineEdit_server_address.setText(SERV)
        self.ui.lineEdit_database_name.setText(CON_DATABASE)
        self.ui.lineEdit_login.setText(USER_LOGIN)
        self.ui.lineEdit_password.setText(USR_PASS)
        self.ui.spinBox_server_port.setValue(CON_PORT)

        self.ui.radio_sql_authentication.setChecked(True)

    def push_info(self, messageStr):
        QtWidgets.QMessageBox.information(self,
                                          "Ошибка в настройках подключения",
                                          messageStr,
                                          QtWidgets.QMessageBox.Ok)
        return

    def validate_connection_settings(self,
                                     driver_name: str,
                                     server_name: str,
                                     port: str,
                                     db_name: str,
                                     sql_login=None,
                                     sql_pass=None) -> bool:

        check_ok = True

        if not server_name:
            self.push_info("Не указано имя сервера")
            check_ok = False
        if check_ok and not driver_name:
            self.push_info("Не указан драйвер")
            check_ok = False
        if check_ok and port == "0":
            self.push_info("Не указан порт")
            check_ok = False
        if check_ok and not db_name:
            self.push_info("Не указано имя базы данных")
            check_ok = False
        if check_ok and sql_login is not None and not sql_login:
            self.push_info("Не указано имя пользователя для подключения к БД")
            check_ok = False
        if check_ok and sql_login is not None and not sql_pass:
            self.push_info("Не указан пароль пользователя для подключения к БД")
            check_ok = False

        return check_ok

    def setSQLPartEnabled(self, lst: list):

        self.ui.groupBox_database_browser.setEnabled(bool(lst))

        # self.ui.comboBox_table_name.setEnabled(True)
        # self.ui.button_show_table.setEnabled(True)
        # self.ui.tableView_database_table.setEnabled(True)

        if bool(lst):
            self.ui.comboBox_table_name.addItems(lst)
        return

    """подсчитаем количество стоблцов в таблицеи вернем их имена в виде списка чтобы сделать цикл для формирования модели в методе show_requested_table"""
    def get_count_col_in_table(self, tableName) -> list:

        sql_q = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE table_catalog = '{self.db_name}' " \
                f"AND TABLE_SCHEMA = '{tableName.split('.')[0]}' AND table_name = '{tableName.split('.')[1]}'"

        if cursor := self.connection.cursor():
            cursor.execute(sql_q)
            records = cursor.fetchall()
            cursor.close()

            column_lst = [str(row[0]) for row in records]

        return column_lst


    # Декоратор слота просто для того чтобы найти в области видимиости в коде
    @QtCore.Slot()
    def connect_to_DB(self):
        self.driver_name = self.ui.lineEdit_driver.text()
        self.server_name = self.ui.lineEdit_server_address.text()
        self.port = self.ui.spinBox_server_port.text()
        self.db_name = self.ui.lineEdit_database_name.text()

        self.sql_login = None
        self.sql_pass = None

        is_windows_auth = self.ui.radio_windows_authentication.isChecked()

        if not is_windows_auth:
            self.sql_login: str = self.ui.lineEdit_login.text()
            self.sql_pass = self.ui.lineEdit_password.text()

        if not self.validate_connection_settings(self.driver_name,
                                                 self.server_name,
                                                 self.port,
                                                 self.db_name,
                                                 self.sql_login,
                                                 self.sql_pass):
            return

        if is_windows_auth:
            self.connection = pyodbc.connect(f"Driver={self.driver_name};"
                                      f"Server={self.server_name};"
                                      f"Database={self.db_name};"
                                      "Trusted_Connection=yes;")
        else:
            connection_str = f"DRIVER={self.driver_name};Server={self.server_name};Port={self.port};DATABASE={self.db_name};UID={self.sql_login};PWD={self.sql_pass}"
            self.connection = pyodbc.connect(connection_str)

        if cursor := self.connection.cursor():

            cursor.execute("SELECT [TABLE_SCHEMA],[TABLE_NAME] FROM information_schema.tables "
                           "WHERE TABLE_TYPE = 'BASE Table' ORDER BY TABLE_SCHEMA, TABLE_NAME ")

            records = cursor.fetchall()
            cursor.close()
            lst = [f"{row[0]}.{row[1]}" for row in records]
            val = len(max(lst, key=len))
            self.ui.comboBox_table_name.setFixedSize(val*6, 20)
            self.setSQLPartEnabled(lst)

    def show_requested_table(self):
        if self.connection is None:
            return

        connection_str = f"DRIVER={self.driver_name};Server={self.server_name};Port={self.port};DATABASE={self.db_name};UID={self.sql_login};PWD={self.sql_pass}"
        db = QSqlDatabase.addDatabase('QODBC')
        db.setDatabaseName(connection_str)
        db.open()

        qry = QSqlQuery(db)
        # todo тут нужно указать запрос. можно указать поля если нужно. так же я бы сделал настройку для выбора ограничения TOP100, TOP1000...
        qry.prepare(f'SELECT TOP 100 * FROM {self.ui.comboBox_table_name.currentText()}')
        qry.exec_()

        model = QSqlTableModel()
        model.setQuery(qry)
        self.ui.tableView_database_table.setModel(model)
        self.ui.tableView_database_table.horizontalHeader().setSectionsMovable(True)

        # self.model = QSqlTableModel(self)
        #
        # if cursor := self.connection.cursor():
        #
        #     col_lst = self.get_count_col_in_table(self.ui.comboBox_table_name.currentText())
        #
        #     self.model.setTable(self.ui.comboBox_table_name.currentText())
        #
        #     self.model.select()
        #
        #     #цикл по кол-ву столбцов для формирования модели
        #     for id, col_name in enumerate(col_lst):
        #         self.model.setHeaderData(id, QtCore.Qt.Horizontal, col_name)
        #
        #     self.ui.tableView_database_table.setModel(self.model)
        #     self.ui.tableView_database_table.horizontalHeader().setSectionsMovable(True)
        #     self.ui.tableView_database_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #
        #     cursor.close()

    def change_to_auth(self):
        auth_methods = self.ui.groupBox_authentication.findChildren(QtWidgets.QRadioButton)
        for auth_method in auth_methods:
            if auth_method.isChecked():
                if auth_method.text() == "Windows authentication":
                    self.ui.lineEdit_login.setEnabled(False)
                    self.ui.lineEdit_login.setText("")
                    self.ui.lineEdit_password.setEnabled(False)
                    self.ui.lineEdit_password.setText("")
                else:
                    self.ui.lineEdit_login.setEnabled(True)
                    self.ui.lineEdit_password.setEnabled(True)

    # События
    def closeEvent(self, event):
        called_from_menu = self.sender() is not None and self.sender().objectName() == "exit_action"

        reply = QtWidgets.QMessageBox.question(self, "Закрыть приложение",
                                               "Закрыть приложение?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if called_from_menu:
            if reply == QtWidgets.QMessageBox.Yes:
                app.exit()
        elif reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    myapp = MySQLViewerForm()
    myapp.show()

    app.exec_()
