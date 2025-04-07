from slides.page import BoxDimension


def test_boxdimension_parse():
    # Test with a string
    box_dim_str = "10pt 20pt none 40pt"
    box_dim_obj = BoxDimension.parse(box_dim_str)
    assert box_dim_obj.left.magnitude == 10
    assert box_dim_obj.top.magnitude == 20
    assert box_dim_obj.right is None
    assert box_dim_obj.bottom.magnitude == 40

    box_dim_str = "10pt"
    box_dim_obj = BoxDimension.parse(box_dim_str)
    assert box_dim_obj.left.magnitude == 10
    assert box_dim_obj.top.magnitude == 10
    assert box_dim_obj.right.magnitude == 10
    assert box_dim_obj.bottom.magnitude == 10

    # Test with None
    parsed_none = BoxDimension.parse(None)
    assert parsed_none is None
