# elektra-fuse

Mount  [elektra](https://github.com/ElektraInitiative/libelektra) as a [fuse(py)](https://github.com/fusepy/fusepy) filesystem.

## Quickstart
Ensure docker is installed, then, to build and run an interactive session:
```sh
./build_container.sh && ./run_new_container.sh
```

The elektra key-hierarchy is now accessible in ~/mount

## Known issues
- Editing a pseudo file ``@elektra.value`` with ``vi/vim`` leads to corruption, other operations work fine (overwriting, moving, etc.) though.
