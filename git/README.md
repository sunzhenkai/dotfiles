# enable

in file '~/.gitconfig' append those texts.

```
[user]
  ...

[includeIf "gitdir:~/.config/git/gitconfig"]
    path = ~/.config/git/gitconfig
```

NOTE: [includeIf...] should follows default [user] at the top
