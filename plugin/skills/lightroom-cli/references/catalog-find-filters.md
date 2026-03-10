# catalog find — Filter Options Reference

## Basic filters

```bash
lr -o json catalog find --rating 5                          # Exact rating
lr -o json catalog find --rating 3 --rating-op ">="         # Rating >= 3
lr -o json catalog find --flag pick                          # Flagged photos
lr -o json catalog find --color-label red                    # Color label
lr -o json catalog find --camera "Canon"                     # Camera model (substring)
```

## Extended filters (v1.2.0)

```bash
lr -o json catalog find --folder-path "2024/vacation"        # Folder path (substring)
lr -o json catalog find --capture-date-from "2024-06-01"     # Captured after date
lr -o json catalog find --capture-date-to "2024-12-31"       # Captured before date
lr -o json catalog find --file-format RAW                    # File format (exact: RAW/DNG/JPEG)
lr -o json catalog find --keyword "landscape"                # Keyword (substring)
lr -o json catalog find --filename "IMG_00"                  # Filename (substring)
```

## Combined filters

```bash
lr -o json catalog find --rating 4 --rating-op ">=" --flag pick --file-format RAW
```

## Notes

- Unknown filter keys return a `warnings` field in the response
- Invalid values (e.g., non-numeric rating) return a validation error
- All string filters use substring matching unless noted otherwise
