---
name: cl-discover
description: "Inwentaryzuje repo i tworzy oparty na dowodach plan z lukami i profilem ryzyka."
---

# cl-discover

1. Odczytaj git status, tree, manifests, istniejące testy i spec. Nie nadpisuj dirty worktree.
2. Zapisz inventory: plik→rola→czy odczytany→source SHA. Sprawdź platform capabilities i settings bez kopiowania sekretów.
3. Oddziel wymagania użytkownika, fakty z repo, założenia odwracalne i blokujące pytania.
4. Wybierz tiny/standard/critical, minimalny vertical slice i acceptance. Przygotuj spec i tasks.json, uruchom gov validate.
5. Przekaż spec niezależnemu spec-auditor. Nie nagrywaj spec approval jako agent.

Wyjście: plik/raport z aktualnym hashem i jawny status. Brak możliwości narzędziowej to BLOCKED/NOT_RUN, nie symulacja wykonania.
