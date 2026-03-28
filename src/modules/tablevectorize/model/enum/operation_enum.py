
class OperationEnum(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    # 没有SELECT，SELECT又不用更新向量