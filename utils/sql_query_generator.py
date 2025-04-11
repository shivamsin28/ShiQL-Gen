class SQLQueryGenerator:
    def select(self, table, columns="*", joins=None, conditions=None, order_by=None, limit=None):
        cols = ', '.join(columns) if isinstance(columns, list) else columns
        query = f"SELECT {cols} FROM {table}"
        
        # Handle joins
        if joins:
            for join in joins:
                join_type = join.get("type", "INNER").upper()
                join_table = join["table"]
                on = join["on"]
                query += f" {join_type} JOIN {join_table} ON {on}"

        # Conditions
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

        # Order
        if order_by:
            query += f" ORDER BY {order_by}"

        # Limit
        if limit:
            query += f" LIMIT {limit}"

        return query + ";"

    def insert(self, table, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f"'{v}'" for v in data.values()])
        return f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"

    def update(self, table, data, conditions=None):
        set_clause = ', '.join([f"{k}='{v}'" for k, v in data.items()])
        query = f"UPDATE {table} SET {set_clause}"
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"
        return query + ";"

    def delete(self, table, conditions=None):
        query = f"DELETE FROM {table}"
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"
        return query + ";"
