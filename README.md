## Lambda Hook for Amazon Lex V2 Book Trip Blueprint

This project provides a sample Python Lambda Hook, that is compatible with the Amazon Lex V2 data structure, and can be used with the Book Trip Blueprint that is described in the “Bot Examples” section of the Amazon Lex Developers Guide (https://docs.aws.amazon.com/lex/latest/dg/ex-book-trip.html). This Lambda Hook can be invoked at the Fulfillment section of both intents included in the bot configuration (BookHotel and BookCar), as well as an initialization and validation function at each turn of the dialog. It includes a sample json to be configured as Test Event for the Lambda Hook, simulating the payload that will be sent by Amazon Lex, when invoking the function.

In the current version of this code, the fulfillment messages have been set in Spanish. The English version of the texts is commented in lines 442 and 517. 

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

