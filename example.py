import slides

from slides import box, text_box, insert_text


def main():
    # credentials = slides.auth.local_oauth(
    #     credentials_path="credentials.json",
    #     encryption_key=b"12345678901234567890123456789012",  # Must be 32 bytes long
    # )

    presentation = slides.open(
        "url of a presentation to add slide to",
        credentials="resource name of the secret in Google Secret Manager",
    )

    tx = presentation.begin()

    tx.slide(
        flex_direction="column",
        justify_content="space-around",
        align_content="center",
    )(
        text_box(
            height="50pt",
            margin="5pt 5pt 5pt 0pt",
            border="1pt",
            border_color="#999",
            content_alignment="middle",
            background_color="#ccc",
            color="#ffffff",
        )(
            insert_text("Big title highlihgiting important thing"),
        ),
        box(
            flex_grow=1,
            flex_direction="row",
            gap="5pt",
            padding="5pt",
        )(
            text_box(
                flex_grow=1,
                alignment="center",
                content_alignment="middle",
                background_color="#0000ff",
                color="#ffffff",
            )(
                insert_text("I'm on the left"),
            ),
            text_box(
                flex_grow=1,
                alignment="center",
                content_alignment="middle",
                background_color="#ff0000",
                color="#ffffff",
            )(
                insert_text("I'm on the right"),
            ),
        ),
    )

    tx.commit()


if __name__ == "__main__":
    main()
