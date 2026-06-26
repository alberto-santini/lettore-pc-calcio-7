# Lettore PC Calcio 7

Questo lettore può essere usato per estrarre programmaticamente informazioni sui calciatori, a partire dalla base di dati originale di PC Calcio 7 e da un file di salvataggio.
Consideratelo come una versione avanzata del "Direttore Tecnico".
L'estrattore produce un file `.csv` che può essere usato per ottenere informazioni molto precise sui calciatori.
Per esempio:
    * Quali calciatori hanno meno di 25 anni, una media di almeno 80, e uno stipendio di al piú 20 milioni di Lire?
    * Quali portieri hanno una media di almeno 86 e sono all'ultimo anno di contratto?
    * Chi sono i mediani spagnoli che giocano in Italia o in Francia, e guadagnano piú di 100 milioni di Lire?

## Funzionamento

Anche se molti parametri sono personalizzabili, questo codice è piú che altro per uso personale.
Io lo uso in questo modo:

* Ho una macchina virtuale UTM (host: macos, guest: Windows XP) con PC Calcio 7 installato in `C:\CALCIO7`.
* Ho una copia di `CALCIO7` sulla mia scrivania (`/Users/alberto/Desktop`).
* Dentro la mia copia di `CALCIO7` ho una cartella chiamata `editor`.
* Il codice è dentro questa cartella `editor`.
